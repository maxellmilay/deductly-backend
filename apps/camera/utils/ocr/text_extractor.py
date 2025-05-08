"""
Text extraction utilities for receipt OCR using multiple methods.
"""

import os
import pytesseract
from openai import OpenAI
from typing import Optional, Dict, Any
import numpy as np
from dotenv import load_dotenv
import cv2

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))


class TextExtractor:
    """Handles text extraction from images using multiple OCR methods."""

    def __init__(self):
        self.tesseract_path = self._find_tesseract_path()
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def _find_tesseract_path(self) -> Optional[str]:
        """Find Tesseract executable path across different platforms."""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows default
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",  # Windows 32-bit
            "/usr/bin/tesseract",  # Linux
            "/usr/local/bin/tesseract",  # macOS
            "/opt/homebrew/bin/tesseract",  # Homebrew on macOS
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def extract_with_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Enhanced text extraction using Tesseract OCR.
        Optimized for Philippine receipt formats.
        """
        if not self.tesseract_path:
            raise Exception("Tesseract not found. Please install Tesseract OCR.")

        # Enhanced configuration for Philippine receipts
        custom_config = (
            "--psm 4 "  # Assume a single column of text of variable sizes
            "--oem 3 "  # Use LSTM OCR Engine
            "-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:/-@₱ "  # Allow common receipt characters including peso sign
            "-l eng+tag+fil"  # Support English, Tagalog, and Filipino
            "-c preserve_interword_spaces=1"  # Preserve spacing between words
            "-c textord_heavy_nr=1"  # Better handling of noisy text
            "-c textord_min_linesize=2.5"  # Better handling of small text
        )

        try:
            # Get text with confidence scores
            data = pytesseract.image_to_data(
                image, config=custom_config, output_type=pytesseract.Output.DICT
            )

            # Process text with confidence scores
            text_lines = []
            current_line = []
            current_y = None
            min_confidence = 60  # Minimum confidence threshold

            for i in range(len(data["text"])):
                if data["conf"][i] > min_confidence:
                    word = data["text"][i].strip()
                    if word:
                        if current_y is None:
                            current_y = data["top"][i]
                        elif abs(data["top"][i] - current_y) > 5:  # New line
                            if current_line:
                                text_lines.append(" ".join(current_line))
                                current_line = []
                            current_y = data["top"][i]
                        current_line.append(word)

            if current_line:
                text_lines.append(" ".join(current_line))

            text = "\n".join(text_lines)

            # Calculate average confidence
            confidences = [conf for conf in data["conf"] if conf != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "text": text.strip(),
                "confidence": avg_confidence,
                "word_data": {
                    "words": data["text"],
                    "confidences": data["conf"],
                    "left": data["left"],
                    "top": data["top"],
                    "width": data["width"],
                    "height": data["height"],
                },
            }

        except Exception as e:
            print(f"Tesseract error: {str(e)}")
            return {"text": "", "confidence": 0, "error": str(e)}

    def extract_with_openai_vision(self, image: np.ndarray) -> Dict[str, Any]:
        """Enhanced text extraction using OpenAI Vision API with Philippine context."""
        try:
            # Convert image to bytes
            _, buffer = cv2.imencode(".png", image)
            image_bytes = buffer.tobytes()
            import base64

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Enhanced prompt for Philippine receipts
            prompt = """
            Extract all text from this Philippine receipt with high accuracy. Focus on:

            1. Store Information:
               - Store/merchant name
               - Branch location
               - TIN (Tax Identification Number)
               - BIR Accreditation Number

            2. Transaction Details:
               - Date and time
               - Receipt number
               - Cashier/Staff ID

            3. Items and Prices:
               - Item descriptions
               - Quantities
               - Unit prices
               - Total per item
               - All amounts in Philippine Peso (₱)

            4. Financial Details:
               - Subtotal
               - VAT (12%)
               - Service charge
               - Discounts
               - Total amount
               - Payment method (Cash, Card, GCash, etc.)

            5. Additional Information:
               - Terms and conditions
               - Return policies
               - Special notes

            Format the response clearly, preserving the original layout and structure.
            Include all numbers and special characters exactly as they appear.
            """

            response = client.chat.completions.create(
                model="gpt-4o",  # or gpt-4-vision-preview if you have access
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=2000,
                temperature=0.1,  # Lower temperature for more consistent output
            )

            return {
                "text": response.choices[0].message.content,
                "model": "gpt-4o",
                "success": True,
            }

        except Exception as e:
            return {"text": "", "error": str(e), "success": False}

    def extract_text(
        self, image: np.ndarray, use_all_methods: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text using available methods with improved result selection.
        """
        results = {}

        # Try Tesseract first
        tesseract_result = self.extract_with_tesseract(image)
        results["tesseract"] = tesseract_result

        # Use OpenAI Vision if requested or if Tesseract confidence is low
        if use_all_methods or tesseract_result.get("confidence", 0) < 70:
            openai_result = self.extract_with_openai_vision(image)
            results["openai_vision"] = openai_result

        # Determine best result
        if use_all_methods and "openai_vision" in results:
            # If both methods were used, choose based on content quality
            tesseract_text = results["tesseract"]["text"]
            openai_text = results["openai_vision"]["text"]

            # Check if OpenAI result contains more structured information
            if len(openai_text.split("\n")) > len(tesseract_text.split("\n")) and any(
                keyword in openai_text.lower()
                for keyword in ["tin", "vat", "total", "₱"]
            ):
                results["best_text"] = openai_text
                results["method_used"] = "openai_vision"
            else:
                results["best_text"] = tesseract_text
                results["method_used"] = "tesseract"
        else:
            results["best_text"] = results["tesseract"]["text"]
            results["method_used"] = "tesseract"

        return results
