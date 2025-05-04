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
import json

logger = logging.getLogger(__name__)


class ImageView(GenericView):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "image"

    @action(detail=False, methods=["POST"])
    def process_receipt(self, request):
        try:
            logger.info("Received process_receipt request")

            # Get the image data from the request
            image_data = request.data.get("image")
            if not image_data:
                logger.error("No image data provided in request")
                return Response(
                    {"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST
                )

            logger.info("Processing image data...")
            # Convert base64 to image
            if isinstance(image_data, str) and image_data.startswith("data:image"):
                # Remove the data URL prefix if present
                image_data = image_data.split("base64,")[1]
                logger.info("Removed data URL prefix")

            try:
                image_bytes = base64.b64decode(image_data)
                logger.info("Successfully decoded base64 image")
            except Exception as e:
                logger.error(f"Failed to decode base64 image: {str(e)}")
                return Response(
                    {"error": "Invalid image data"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Process the receipt using ReceiptProcessor
            logger.info("Starting receipt processing...")
            processor = ReceiptProcessor()

            # Process receipt using the combined method with debug info
            result = processor.process_receipt(image_bytes, return_debug_info=True)
            logger.info(
                f"Receipt processing complete. Result: {json.dumps(result, indent=2)}"
            )

            if not result.get("success"):
                logger.error(f"Receipt processing failed: {result.get('error')}")
                return Response(
                    {"error": result.get("error", "Failed to process receipt")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"success": True, "data": result.get("data")}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error processing receipt: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
