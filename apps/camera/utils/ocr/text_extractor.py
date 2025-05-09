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
from functools import lru_cache
import hashlib
import logging
import json

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextExtractor:
    """Handles text extraction from images using multiple OCR methods."""

    def __init__(self):
        self.tesseract_path = self._find_tesseract_path()
        self.tessdata_path = self._find_tessdata_path()

        if self.tesseract_path:
            logger.info(f"Found Tesseract at: {self.tesseract_path}")
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

        if self.tessdata_path:
            logger.info(f"Found tessdata at: {self.tessdata_path}")
            os.environ["TESSDATA_PREFIX"] = self.tessdata_path
            # Verify language files exist
            self._verify_language_files()
        else:
            logger.error("Tessdata directory not found!")

        # Cache size for OCR results
        self._cache_size = 100
        self._cache = {}

    def _verify_language_files(self):
        """Verify that required language files exist."""
        required_files = ["eng.traineddata"]
        for file in required_files:
            file_path = os.path.join(self.tessdata_path, file)
            if os.path.exists(file_path):
                logger.info(f"Found language file: {file}")
            else:
                logger.error(f"Missing language file: {file} at {file_path}")

    def _find_tesseract_path(self) -> Optional[str]:
        """Find Tesseract executable path across different platforms."""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows default
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",  # Windows 32-bit
            "/usr/bin/tesseract",  # Linux
            "/usr/local/bin/tesseract",  # macOS
            "/opt/homebrew/bin/tesseract",  # Homebrew
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def _find_tessdata_path(self) -> Optional[str]:
        """Find Tesseract data directory path across different platforms."""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tessdata",  # Windows default
            r"C:\Program Files (x86)\Tesseract-OCR\tessdata",  # Windows 32-bit
            "/usr/share/tessdata",  # Linux
            "/usr/local/share/tessdata",  # macOS
            "/opt/homebrew/share/tessdata",  # Homebrew
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def _get_image_hash(self, image: np.ndarray) -> str:
        """Generate a hash for the image to use as cache key."""
        return hashlib.md5(image.tobytes()).hexdigest()

    def extract_with_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Enhanced text extraction using Tesseract OCR.
        Optimized for Philippine receipt formats.
        """
        if not self.tesseract_path:
            raise Exception("Tesseract not found. Please install Tesseract OCR.")

        if not self.tessdata_path:
            raise Exception(
                "Tesseract data directory not found. Please ensure tessdata is installed."
            )

        # Check cache first
        image_hash = self._get_image_hash(image)
        if image_hash in self._cache:
            return self._cache[image_hash]

        # Log current Tesseract configuration
        logger.info(f"Tesseract path: {self.tesseract_path}")
        logger.info(f"Tessdata path: {self.tessdata_path}")
        logger.info(f"TESSDATA_PREFIX: {os.environ.get('TESSDATA_PREFIX')}")

        # Optimized configuration for Philippine receipts
        custom_config = (
            "--psm 4 "  # Assume a single column of text of variable sizes
            "--oem 1 "  # Use Legacy + LSTM engines (faster than pure LSTM)
            "-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:/-@₱ "  # Allow common receipt characters
            "-l eng "  # Use English language
            "-c preserve_interword_spaces=1 "  # Preserve spacing between words
            "-c textord_heavy_nr=1 "  # Better handling of noisy text
            "-c textord_min_linesize=2.5"  # Better handling of small text
        )

        try:
            # Get text with confidence scores
            logger.info("Attempting OCR with config: " + custom_config)
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

            result = {
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

            # Cache the result
            if len(self._cache) >= self._cache_size:
                # Remove oldest item if cache is full
                self._cache.pop(next(iter(self._cache)))
            self._cache[image_hash] = result

            return result

        except Exception as e:
            logger.error(f"Tesseract error: {str(e)}")
            return {"text": "", "confidence": 0, "error": str(e)}

    def extract_with_openai_vision(self, image: np.ndarray) -> Dict[str, Any]:
        """Enhanced text extraction using OpenAI Vision API with Philippine context."""
        try:
            # Convert image to bytes
            _, buffer = cv2.imencode(".png", image)
            image_bytes = buffer.tobytes()
            import base64

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Enhanced prompt for Philippine receipts that returns data in our exact format
            prompt = """
            Extract and structure the following receipt information in JSON format. 
            This is a Philippine receipt, so look for:
            - Store name and TIN (Tax Identification Number)
            - Date and time
            - Items with quantities and prices
            - VAT (12%)
            - Service charge
            - Discounts
            - Payment method (Cash, Card, GCash, etc.)
            - Total amount
            
            Format the response as a JSON object with these fields:
            {
                "store_info": {
                    "name": "store name",
                    "tin": "TIN number if available",
                    "branch": "branch name if available"
                },
                "transaction_info": {
                    "date": "date in YYYY-MM-DD format",
                    "time": "time in HH:MM:SS format",
                    "payment_method": "payment method"
                },
                "items": [
                    {
                        "name": "item name",
                        "quantity": "quantity",
                        "price": "price"
                    }
                ],
                "totals": {
                    "subtotal": "subtotal",
                    "vat": "VAT amount",
                    "service_charge": "service charge",
                    "discount": "discount amount",
                    "total": "total amount"
                },
                "metadata": {
                    "currency": "PHP",
                    "vat_rate": 0.12,
                    "bir_accreditation": "BIR accreditation number if available",
                    "serial_number": "serial number if available"
                }
            }

            Important:
            1. Return ONLY the JSON object, no additional text
            2. Use proper number formatting (e.g., "185.00" not "185")
            3. Convert dates to YYYY-MM-DD format
            4. Convert times to 24-hour format (HH:MM:SS)
            5. Include all available information
            6. If a field is not found, use null or empty string
            """

            response = client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o model
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

            # Parse the response as JSON
            try:
                result_text = response.choices[0].message.content
                # Find JSON in the response (in case there's any additional text)
                import re

                json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                    return {
                        "text": result_text,  # Keep original text for debugging
                        "parsed_data": result_json,  # Add parsed data
                        "model": "gpt-4o",
                        "success": True,
                    }
                else:
                    logger.error("No JSON found in Vision API response")
                    return {
                        "text": result_text,
                        "error": "No JSON found in response",
                        "success": False,
                    }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from response: {str(e)}")
                return {
                    "text": result_text,
                    "error": f"JSON parsing error: {str(e)}",
                    "success": False,
                }

        except Exception as e:
            logger.error(f"OpenAI Vision API error: {str(e)}")
            return {"text": "", "error": str(e), "success": False}

    def extract_text(
        self, image: np.ndarray, use_all_methods: bool = False
    ) -> Dict[str, Any]:
        """
        Extract text using available methods with improved result selection.
        Optimized to use Tesseract by default and OpenAI Vision only when needed.
        """
        results = {}

        # Try Tesseract first
        tesseract_result = self.extract_with_tesseract(image)
        results["tesseract"] = tesseract_result

        # Check if Tesseract failed or produced empty text
        if (
            not tesseract_result.get("text")
            or tesseract_result.get("confidence", 0) < 50
        ):
            logger.info(
                "Tesseract failed or produced low confidence results, falling back to OpenAI Vision"
            )
            openai_result = self.extract_with_openai_vision(image)
            results["openai_vision"] = openai_result
            results["best_text"] = openai_result.get("text", "")
            results["method_used"] = "openai_vision"
        else:
            results["best_text"] = tesseract_result["text"]
            results["method_used"] = "tesseract"

        # If use_all_methods is True, try both methods regardless of Tesseract's success
        if use_all_methods and results["method_used"] == "tesseract":
            openai_result = self.extract_with_openai_vision(image)
            results["openai_vision"] = openai_result

            # Choose best result based on content quality
            tesseract_text = results["tesseract"]["text"]
            openai_text = results["openai_vision"]["text"]

            if len(openai_text.split("\n")) > len(tesseract_text.split("\n")) and any(
                keyword in openai_text.lower()
                for keyword in ["tin", "vat", "total", "₱"]
            ):
                results["best_text"] = openai_text
                results["method_used"] = "openai_vision"

        return results
