"""
Text extraction utilities for receipt OCR using multiple methods.
"""

import os
import pytesseract
import openai
from typing import Optional, Dict, Any
import numpy as np
from dotenv import load_dotenv
import cv2

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPEN_AI_API_KEY")


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
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def extract_with_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract text using Tesseract OCR.
        Optimized for Philippine receipt formats.
        """
        if not self.tesseract_path:
            raise Exception("Tesseract not found. Please install Tesseract OCR.")

        # Configure Tesseract for receipt text
        custom_config = (
            "--psm 6 "  # Assume uniform block of text
            "--oem 3 "  # Use LSTM OCR Engine
            "-c tessedit_char_blacklist=@#$%^&*()_+=[]{}|\\<>~"
            "-l eng+tag"  # Support both English and Tagalog
        )

        try:
            # Get text
            text = pytesseract.image_to_string(image, config=custom_config)

            # Get confidence scores
            data = pytesseract.image_to_data(
                image, config=custom_config, output_type=pytesseract.Output.DICT
            )

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
            return {"text": "", "confidence": 0, "error": str(e)}

    def extract_with_openai_vision(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text using OpenAI Vision API with Philippine context."""
        try:
            # Convert image to bytes
            _, buffer = cv2.imencode(".png", image)
            image_bytes = buffer.tobytes()

            # Craft prompt for Philippine context
            prompt = """
            Extract all text from this receipt, focusing on:
            1. Store/merchant name (including branch if available)
            2. TIN number (Tax Identification Number)
            3. Date and time
            4. Items and prices (in PHP)
            5. VAT details
            6. Total amount
            7. Any special Philippine-specific details (e.g., BIR accreditation)
            
            Format the response in a clear, structured way.
            """

            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
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

            return {
                "text": response.choices[0].message.content,
                "model": "gpt-4-vision-preview",
                "success": True,
            }

        except Exception as e:
            return {"text": "", "error": str(e), "success": False}

    def extract_text(
        self, image: np.ndarray, use_all_methods: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text using available methods.
        Returns results from all methods if use_all_methods is True.
        """
        results = {}

        # Always try Tesseract first
        tesseract_result = self.extract_with_tesseract(image)
        results["tesseract"] = tesseract_result

        # Use OpenAI Vision if requested and Tesseract confidence is low
        if use_all_methods or tesseract_result.get("confidence", 0) < 60:
            openai_result = self.extract_with_openai_vision(image)
            results["openai_vision"] = openai_result

        # Determine best result
        if use_all_methods:
            # If both methods were used, choose the better one
            if "openai_vision" in results and results["openai_vision"]["success"]:
                results["best_text"] = results["openai_vision"]["text"]
                results["method_used"] = "openai_vision"
            else:
                results["best_text"] = results["tesseract"]["text"]
                results["method_used"] = "tesseract"
        else:
            results["best_text"] = results["tesseract"]["text"]
            results["method_used"] = "tesseract"

        return results
