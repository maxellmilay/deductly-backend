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
from .utils.cloudinary import upload_base64_image
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

    def _upload_to_cloudinary_async(self, image_data, result, user):
        """Asynchronously upload image to Cloudinary and update result."""
        try:
            cloudinary_result = upload_base64_image(image_data)
            if cloudinary_result.get("success"):
                public_url = cloudinary_result.get("public_url")
                public_id = cloudinary_result.get("public_id")
                result["data"]["image_url"] = public_url

                # Create Image instance
                Image.objects.create(title=public_id, user=user, image_url=public_url)
                logger.info(
                    "Successfully uploaded image to Cloudinary and created Image instance"
                )
        except Exception as e:
            logger.error(f"Error in async Cloudinary upload: {str(e)}")

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
                    image_url="",  # This will be updated later if needed
                )
                logger.info(f"ReceiptImage record created with ID: {receipt_image.id}")
            except Exception as e:
                logger.error(f"Error creating receipt image record: {str(e)}")
                return Response(
                    {"error": f"Failed to create receipt image record: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

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
                    total_expediture=float(
                        data.get("totals", {}).get("total_expediture", 0)
                    ),
                    payment_method=data.get("transaction_info", {}).get(
                        "payment_method", ""
                    ),
                    vendor=vendor,
                    discount=float(data.get("totals", {}).get("discount", 0)),
                    value_added_tax=float(
                        data.get("totals", {}).get("value_added_tax", 0)
                    ),
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
                        price=float(item_data.get("price", 0)),
                        subtotal_expenditure=float(item_data.get("subtotal", 0)),
                        receipt=receipt,
                        deductable_amount=float(item_data.get("deductible_amount", 0)),
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

            return Response({"success": True, "receipt_id": receipt.id})

        except Exception as e:
            logger.error(f"Error saving receipt: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
