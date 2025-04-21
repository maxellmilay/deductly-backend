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


class ImageView(GenericView):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "image"

    @action(detail=False, methods=["POST"])
    def process_receipt(self, request):
        try:
            # Get the image data from the request
            image_data = request.data.get("image")
            if not image_data:
                return Response(
                    {"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Convert base64 to image
            if isinstance(image_data, str) and image_data.startswith("data:image"):
                # Remove the data URL prefix if present
                image_data = image_data.split("base64,")[1]

            image_bytes = base64.b64decode(image_data)
            image = PILImage.open(io.BytesIO(image_bytes))

            # Process the receipt
            preprocessor = ImagePreprocessor()
            text_extractor = TextExtractor()
            receipt_parser = ReceiptParser()
            processor = ReceiptProcessor()

            # Preprocess image
            processed_image = preprocessor.process(image)

            # Extract text
            extracted_text = text_extractor.extract(processed_image)

            # Parse receipt
            parsed_data = receipt_parser.parse(extracted_text)

            # Process receipt data
            result = processor.process(parsed_data)

            return Response(
                {"success": True, "data": result}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
