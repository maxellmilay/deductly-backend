from main.utils.generic_api import GenericView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImageSerializer
from .models import Image
from rest_framework.permissions import IsAuthenticated
from .utils.ocr import ImagePreprocessor, TextExtractor, ReceiptParser, ReceiptProcessor
import base64
import io
from PIL import Image as PILImage
import logging

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
                image = PILImage.open(io.BytesIO(image_bytes))
                logger.info("Successfully decoded base64 image")
            except Exception as e:
                logger.error(f"Failed to decode base64 image: {str(e)}")
                return Response(
                    {"error": "Invalid image data"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Process the receipt
            logger.info("Starting OCR processing...")
            preprocessor = ImagePreprocessor()
            text_extractor = TextExtractor()
            receipt_parser = ReceiptParser()
            processor = ReceiptProcessor()

            # Preprocess image
            processed_image = preprocessor.process(image)
            logger.info("Image preprocessing complete")

            # Extract text
            extracted_text = text_extractor.extract(processed_image)
            logger.info("Text extraction complete")

            # Parse receipt
            parsed_data = receipt_parser.parse(extracted_text)
            logger.info("Receipt parsing complete")

            # Process receipt data
            result = processor.process(parsed_data)
            logger.info("Receipt processing complete")

            return Response(
                {"success": True, "data": result}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error processing receipt: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
