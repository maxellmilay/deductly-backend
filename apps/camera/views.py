from main.utils.generic_api import GenericView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImageSerializer
from .models import Image
from rest_framework.permissions import IsAuthenticated
from .utils.ocr import ReceiptProcessor
import logging
import numpy as np
import json
from .utils.cloudinary import upload_base64_image
import threading
from django.views.decorators.gzip import gzip_page
from django.utils.decorators import method_decorator
import cv2
import io
from PIL import Image as PILImage
import cloudinary.uploader

logger = logging.getLogger(__name__)


class ImageView(GenericView):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "image"

    def _upload_to_cloudinary_async(self, image_file, result):
        """Asynchronously upload image to Cloudinary and update result."""
        try:
            # Convert to bytes for direct upload
            _, buffer = cv2.imencode(".jpg", image_file)

            # Direct upload to Cloudinary
            cloudinary_result = cloudinary.uploader.upload(
                buffer.tobytes(), resource_type="image", format="jpg", folder="receipts"
            )

            if cloudinary_result:
                result["data"]["image_url"] = cloudinary_result.get("secure_url")
                logger.info("Successfully uploaded image to Cloudinary asynchronously")
        except Exception as e:
            logger.error(f"Error in async Cloudinary upload: {str(e)}")

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

            logger.info("Processing image file...")
            try:
                # Read image file directly into numpy array
                image_bytes = image_file.read()
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                logger.info("Successfully loaded image file")
            except Exception as e:
                logger.error(f"Failed to load image file: {str(e)}")
                return Response(
                    {"error": "Invalid image file"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Process the receipt using ReceiptProcessor
            logger.info("Starting receipt processing...")
            processor = ReceiptProcessor()

            # Process receipt using the combined method with debug info
            result = processor.process_receipt(
                image, return_debug_info=False
            )  # Set to False to reduce response size
            logger.info("Receipt processing complete")

            if not result.get("success"):
                logger.error(f"Receipt processing failed: {result.get('error')}")
                return Response(
                    {"error": result.get("error", "Failed to process receipt")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Start async Cloudinary upload
            upload_thread = threading.Thread(
                target=self._upload_to_cloudinary_async, args=(image, result)
            )
            upload_thread.start()

            # Prepare minimal response data
            response_data = {"success": True, "data": result.get("data")}

            # Return response immediately with receipt data
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing receipt: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
