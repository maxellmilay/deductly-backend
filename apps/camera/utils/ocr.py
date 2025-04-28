import os
import cv2
import numpy as np
import pytesseract
import io
import csv
import re
from typing import Tuple, List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))


class ReceiptProcessor:
    def __init__(self):
        # Try to find Tesseract executable in common locations
        self.tesseract_path = self._find_tesseract_path()
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def _find_tesseract_path(self) -> Optional[str]:
        """Find Tesseract executable path across different platforms"""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows default
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",  # Windows 32-bit
            "/usr/bin/tesseract",  # Linux
            "/usr/local/bin/tesseract",  # macOS
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def detect_and_crop_receipt(self, image: np.ndarray) -> np.ndarray:
        """Detect receipt edges and crop the image"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while keeping edges sharp
        blur = cv2.bilateralFilter(gray, 9, 75, 75)

        # Apply Canny edge detection
        edges = cv2.Canny(blur, 50, 150)

        # Dilate edges to connect any broken lines
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return image

        # Find the largest contour (should be the receipt)
        receipt_contour = max(contours, key=cv2.contourArea)

        # Get the minimum area rectangle
        rect = cv2.minAreaRect(receipt_contour)
        box = cv2.boxPoints(rect)
        box = np.int32(box)

        # Get width and height of the receipt
        width = int(rect[1][0])
        height = int(rect[1][1])

        # Source points
        src_pts = box.astype("float32")

        # Destination points
        dst_pts = np.array(
            [[0, height - 1], [0, 0], [width - 1, 0], [width - 1, height - 1]],
            dtype="float32",
        )

        # Get perspective transform matrix
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)

        # Warp the image
        warped = cv2.warpPerspective(image, M, (width, height))

        return warped

    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for OCR"""
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Resize to a larger height while maintaining aspect ratio
        height = 2000
        aspect_ratio = gray.shape[1] / gray.shape[0]
        width = int(height * aspect_ratio)
        resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

        # Simple binary thresholding
        _, binary = cv2.threshold(resized, 180, 255, cv2.THRESH_BINARY)

        # Add white border
        border_size = 20
        with_border = cv2.copyMakeBorder(
            binary,
            border_size,
            border_size,
            border_size,
            border_size,
            cv2.BORDER_CONSTANT,
            value=255,
        )

        return with_border

    def extract_text_with_tesseract(self, image: np.ndarray) -> str:
        """Extract text using Tesseract OCR"""
        if not self.tesseract_path:
            raise Exception("Tesseract not found. Please install Tesseract OCR.")

        # Configure Tesseract for receipt text
        custom_config = (
            "--psm 6 "  # Assume uniform block of text
            "--oem 3 "  # Use LSTM OCR Engine
            "-c tessedit_char_blacklist=@#$%^&*()_+=[]{}|\\<>~"
        )

        # Extract text
        text = pytesseract.image_to_string(image, config=custom_config, lang="eng")
        return text.strip()

    def extract_text_with_openai_vision(self, image: np.ndarray) -> str:
        """Extract text using OpenAI Vision API"""
        # Convert image to bytes
        _, buffer = cv2.imencode(".png", image)
        image_bytes = buffer.tobytes()

        try:
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this receipt. Focus on items, prices, dates, and store information. Format the response in a clear, structured way.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_bytes}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI Vision API error: {str(e)}")

    def process_receipt(self, image_file: bytes) -> Tuple[str, List[Dict[str, str]]]:
        """Process receipt image and extract text using both methods"""
        try:
            # Read image file
            file_bytes = np.asarray(bytearray(image_file), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            if image is None:
                raise Exception("Failed to load image")

            # Preprocess the image
            processed = self.preprocess_for_ocr(image)

            # Try both methods
            tesseract_text = self.extract_text_with_tesseract(processed)
            openai_text = self.extract_text_with_openai_vision(processed)

            # Parse the text into structured data
            structured_data = self.parse_receipt_text(tesseract_text)

            # Return both texts and structured data
            return {
                "tesseract_text": tesseract_text,
                "openai_text": openai_text,
                "structured_data": structured_data,
            }

        except Exception as e:
            raise Exception(f"Error processing receipt image: {str(e)}")

    def parse_receipt_text(self, text: str) -> List[Dict[str, str]]:
        """Parse receipt text into structured data"""
        lines = text.split("\n")
        items = []

        # Match price formats: XX.XX or $XX.XX
        price_pattern = r"\$?\d+\.\d+"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Find all prices in the line
            prices = re.findall(price_pattern, line)

            if prices:
                # Get the last price (usually the item price)
                price = prices[-1]
                # Get everything before the price as description
                description = line[: line.rfind(price)].strip()

                if description:
                    items.append({"description": description, "price": price})
            else:
                # Keep non-price lines that might be important
                if len(line) > 3 and not line.isspace():
                    items.append({"description": line, "price": ""})

        return items

    def generate_csv(self, structured_data: List[Dict[str, str]]) -> str:
        """Generate CSV from structured data"""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["description", "price"])
        writer.writeheader()

        for item in structured_data:
            if item["description"].strip():
                writer.writerow(
                    {
                        "description": item["description"].strip(),
                        "price": item["price"].strip(),
                    }
                )

        return output.getvalue()
