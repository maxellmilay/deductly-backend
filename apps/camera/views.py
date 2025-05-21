from main.utils.generic_api import GenericView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImageSerializer
from .models import Image
from rest_framework.permissions import IsAuthenticated
from .utils.ocr import ReceiptProcessor
import base64
import io
from PIL import Image as PILImage
import logging
import numpy as np
from .utils.cloudinary import upload_base64_image, upload_base64_pdf
import threading
from django.views.decorators.gzip import gzip_page
from django.utils.decorators import method_decorator
import cv2
import io
from PIL import Image as PILImage
from datetime import datetime
from apps.receipt.models import Receipt, ReceiptItem, Vendor, ReceiptImage
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from decimal import Decimal

logger = logging.getLogger(__name__)


class ImageView(GenericView):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated]

    def filter_queryset(self, filters, excludes):
        filters["user"] = self.request.user
        filter_q = Q(**filters)
        exclude_q = Q(**excludes)
        return self.queryset.filter(filter_q).exclude(exclude_q)

    def _format_number(self, value):
        """Convert string number with commas to float."""
        if not value:
            return 0.0
        try:
            # Remove commas and convert to float
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    def _create_or_update_report(self, user, receipt_date, total_amount, vat):
        """Create or update reports for weekly, monthly, and yearly periods."""
        from apps.report.models import Report
        from datetime import datetime, timedelta
        import calendar

        # Helper function to get period dates
        def get_period_dates(date, period_type):
            if period_type == "WEEKLY":
                # Get the start of the week (Monday)
                start_date = date - timedelta(days=date.weekday())
                end_date = start_date + timedelta(days=6)
            elif period_type == "MONTHLY":
                # Get the start and end of the month
                start_date = date.replace(day=1)
                end_date = date.replace(
                    day=calendar.monthrange(date.year, date.month)[1]
                )
            else:  # YEARLY
                # Get the start and end of the year
                start_date = date.replace(month=1, day=1)
                end_date = date.replace(month=12, day=31)
            return start_date, end_date

        # Convert amounts to Decimal
        total_amount = Decimal(str(total_amount))
        vat = Decimal(str(vat))

        # Create or update reports for all periods
        for period_type in ["WEEKLY", "MONTHLY", "YEARLY"]:
            start_date, end_date = get_period_dates(receipt_date, period_type)

            # Check if receipt date falls within this period
            if start_date <= receipt_date <= end_date:
                report, created = Report.objects.get_or_create(
                    user=user,
                    category=period_type,
                    start_date=start_date,
                    end_date=end_date,
                    defaults={
                        "title": f"{period_type} Report {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                        "grand_total_expenditure": total_amount,
                        "total_tax_deductions": vat,
                    },
                )

                if not created:
                    # Update existing report
                    report.grand_total_expenditure = (
                        Decimal(str(report.grand_total_expenditure)) + total_amount
                    )
                    report.total_tax_deductions = (
                        Decimal(str(report.total_tax_deductions)) + vat
                    )
                    report.save()

                logger.info(
                    f"{'Created' if created else 'Updated'} {period_type} Report with ID: {report.id}"
                )

    def _upload_to_cloudinary_async(self, image_data, result, user):
        """Asynchronously upload image to Cloudinary and update result."""
        try:
            # First upload the image
            image_result = upload_base64_image(image_data)
            if not image_result.get("success"):
                raise Exception("Failed to upload image to Cloudinary")

            image_url = image_result.get("public_url")
            result["data"]["image_url"] = image_url

            # Get vendor name from result data or use default
            vendor_name = (
                result.get("data", {})
                .get("store_info", {})
                .get("name", "Unknown Vendor")
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create Image instance
            image = Image.objects.create(
                title=f"Receipt from {vendor_name} - {timestamp}",
                user=user,
                image_url=image_url,
            )
            logger.info(
                "Successfully uploaded image to Cloudinary and created Image instance"
            )

            # Create Document instance first with image URL
            from apps.document.models import Document

            document = Document.objects.create(
                title=f"Document for {vendor_name} - {timestamp}",
                document_url=image_url,  # Initially set to image URL
                user=user,
                type="RECEIPT",
            )
            logger.info(f"Created Document instance with ID: {document.id}")

            # Generate PDF from scan results
            try:
                from .utils.pdf_generator import generate_receipt_pdf

                pdf_data = generate_receipt_pdf(result["data"])

                # Upload PDF to Cloudinary
                pdf_result = upload_base64_pdf(pdf_data, vendor_name)
                if pdf_result.get("success"):
                    pdf_url = pdf_result.get("public_url")
                    logger.info(f"PDF URL: {pdf_url}")
                    # Update document with PDF URL
                    document.document_url = pdf_url
                    document.save()
                    logger.info(f"Successfully uploaded PDF and updated document URL")
                else:
                    logger.error("Failed to upload PDF to Cloudinary")
            except Exception as e:
                logger.error(f"Error generating or uploading PDF: {str(e)}")

            # Add document ID to result for receipt creation
            if result.get("data"):
                result["data"]["document_id"] = document.id

        except Exception as e:
            logger.error(
                f"Error in async Cloudinary upload and related operations: {str(e)}"
            )

    @method_decorator(csrf_exempt)
    @method_decorator(gzip_page)
    @action(detail=False, methods=["POST"])
    def process_receipt(self, request):
        try:
            logger.info("Received process_receipt request")

            # Get the image file from the request
            image_file = request.FILES.get("image")
            if not image_file:
                logger.error("No image file provided in request")
                return Response(
                    {"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST
                )

            logger.info("Processing image data...")

            # Handle file upload
            if hasattr(image_file, "read"):
                try:
                    image_bytes = image_file.read()
                    logger.info("Successfully read uploaded file")
                except Exception as e:
                    logger.error(f"Failed to read uploaded file: {str(e)}")
                    return Response(
                        {"error": "Invalid file upload"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            # Handle base64 string
            else:
                if isinstance(image_file, str) and image_file.startswith("data:image"):
                    # Remove the data URL prefix if present
                    image_file = image_file.split("base64,")[1]
                    logger.info("Removed data URL prefix")

                try:
                    image_bytes = base64.b64decode(image_file)
                    logger.info("Successfully decoded base64 image")
                except Exception as e:
                    logger.error(f"Failed to decode base64 image: {str(e)}")
                    return Response(
                        {"error": "Invalid image data"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Process the receipt using ReceiptProcessor
            logger.info("Starting receipt processing...")
            processor = ReceiptProcessor()

            try:
                # Convert image_bytes to PIL Image for processing
                image = PILImage.open(io.BytesIO(image_bytes))
                # Convert to numpy array for OpenCV processing
                image_np = np.array(image)
                # Convert RGB to BGR (OpenCV format)
                if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

                # Process receipt using the combined method with debug info
                result = processor.process_receipt(
                    image_np, return_debug_info=False
                )  # Set to False to reduce response size
                logger.info("Receipt processing complete")
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                return Response(
                    {"error": f"Failed to process image: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if not result.get("success"):
                logger.error(f"Receipt processing failed: {result.get('error')}")
                return Response(
                    {"error": result.get("error", "Failed to process receipt")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Convert image_bytes to base64 for Cloudinary upload if it's from file upload
            if hasattr(image_file, "read"):
                image_file = base64.b64encode(image_bytes).decode("utf-8")

            # Start async Cloudinary upload
            logger.info(f"TESTING USER REQUEST: {request.user.__dict__}")
            upload_thread = threading.Thread(
                target=self._upload_to_cloudinary_async,
                args=(image_file, result, request.user),
            )
            upload_thread.start()

            # Save the extracted data to database only if user is authenticated
            if (
                request.user.is_authenticated
                and result.get("success")
                and result.get("data")
            ):
                try:
                    # Create Image record first
                    image_record = Image.objects.create(
                        title=f"Receipt Image {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        user=request.user,
                        image_url="",  # Will be updated by async upload
                    )

                    # Save receipt data
                    save_result = processor.text_extractor.save_to_database(
                        result["data"],
                        user_id=request.user.id,
                        image_id=image_record.id,
                    )

                    if not save_result["success"]:
                        logger.error(
                            f"Failed to save receipt data: {save_result.get('error')}"
                        )
                        # Continue with response even if save fails

                    result["data"]["receipt_id"] = save_result.get("receipt_id")
                except Exception as e:
                    logger.error(f"Error saving to database: {str(e)}")
                    # Continue with response even if save fails

            # Prepare minimal response data
            response_data = {"success": True, "data": result.get("data")}

            # Return response immediately with receipt data
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing receipt: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=["POST"])
    def save_receipt(self, request):
        try:
            logger.info("Received save_receipt request")
            logger.info(f"Request data: {request.data}")

            data = request.data

            # Create or get vendor
            vendor_data = data.get("store_info", {})
            logger.info(f"Creating/updating vendor with data: {vendor_data}")

            try:
                vendor, created = Vendor.objects.get_or_create(
                    name=vendor_data.get("name", "Unknown Vendor"),
                    defaults={
                        "address": vendor_data.get("address", ""),
                        "email": vendor_data.get("email", ""),
                        "contact_number": vendor_data.get("contact_number", ""),
                        "establishment": vendor_data.get(
                            "establishment", vendor_data.get("name", "Unknown Vendor")
                        ),
                    },
                )
                logger.info(
                    f"Vendor {'created' if created else 'retrieved'}: {vendor.name}"
                )
            except Exception as e:
                logger.error(f"Error creating/updating vendor: {str(e)}")
                return Response(
                    {"error": f"Failed to create/update vendor: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Create ReceiptImage record first
            try:
                receipt_image = ReceiptImage.objects.create(
                    title=f"Receipt Image {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    user=request.user if request.user.is_authenticated else None,
                    image_url=data.get("image_url", ""),  # Get image URL from data
                )
                logger.info(f"ReceiptImage record created with ID: {receipt_image.id}")
            except Exception as e:
                logger.error(f"Error creating receipt image record: {str(e)}")
                return Response(
                    {"error": f"Failed to create receipt image record: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Format numbers properly
            totals = data.get("totals", {})
            total_amount = self._format_number(totals.get("total_expediture", 0))
            discount = self._format_number(totals.get("discount", 0))
            vat = self._format_number(totals.get("value_added_tax", 0))

            # Create receipt
            logger.info("Creating receipt record")
            try:
                receipt = Receipt.objects.create(
                    title=f"Receipt from {vendor.name}",
                    user=request.user if request.user.is_authenticated else None,
                    category=data.get("metadata", {}).get(
                        "transaction_category", "OTHER"
                    ),
                    image=receipt_image,  # Link to the created receipt image
                    total_expediture=total_amount,
                    payment_method=data.get("transaction_info", {}).get(
                        "payment_method", ""
                    ),
                    vendor=vendor,
                    discount=discount,
                    value_added_tax=vat,
                    document_id=data.get(
                        "document_id"
                    ),  # Link to document if available
                )
                logger.info(f"Receipt created with ID: {receipt.id}")
            except Exception as e:
                logger.error(f"Error creating receipt: {str(e)}")
                # Clean up the receipt image record if receipt creation fails
                receipt_image.delete()
                return Response(
                    {"error": f"Failed to create receipt: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Create receipt items
            items_data = data.get("items", [])
            logger.info(f"Creating {len(items_data)} receipt items")
            try:
                for item_data in items_data:
                    ReceiptItem.objects.create(
                        title=item_data.get("title", ""),
                        quantity=int(item_data.get("quantity", 1)),
                        price=self._format_number(item_data.get("price", 0)),
                        subtotal_expenditure=self._format_number(
                            item_data.get("subtotal", 0)
                        ),
                        receipt=receipt,
                        deductable_amount=self._format_number(
                            item_data.get("deductible_amount", 0)
                        ),
                    )
                logger.info("All receipt items created successfully")
            except Exception as e:
                logger.error(f"Error creating receipt items: {str(e)}")
                # Delete both receipt and receipt image if items creation fails
                receipt.delete()
                receipt_image.delete()
                return Response(
                    {"error": f"Failed to create receipt items: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Create or update reports based on receipt date
            try:
                receipt_date = datetime.strptime(
                    data.get("transaction_info", {}).get(
                        "date", datetime.now().strftime("%Y-%m-%d")
                    ),
                    "%Y-%m-%d",
                )
                self._create_or_update_report(
                    request.user, receipt_date, total_amount, vat
                )
                logger.info("Successfully created/updated reports")
            except Exception as e:
                logger.error(f"Error creating/updating reports: {str(e)}")
                # Don't fail the whole request if report creation fails
                # Just log the error and continue

            return Response({"success": True, "receipt_id": receipt.id})

        except Exception as e:
            logger.error(f"Error saving receipt: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
