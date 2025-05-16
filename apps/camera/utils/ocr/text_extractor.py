"""
Text extraction utilities for receipt OCR using OpenAI Vision API.
"""

import os
from openai import OpenAI
from typing import Dict, Any
import numpy as np
from dotenv import load_dotenv
import cv2
import base64
import logging
import json
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

# Create a thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=2)


class TextExtractor:
    """Handles text extraction from images using OpenAI Vision API."""

    def __init__(self):
        self._image_cache = {}  # Simple cache for processed images

    def _optimize_image(self, image: np.ndarray) -> tuple:
        """Optimize image for API with minimal processing."""
        try:
            # Optimize image size for API
            max_dimension = 1024
            height, width = image.shape[:2]

            if max(height, width) > max_dimension:
                scale = max_dimension / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(
                    image, (new_width, new_height), interpolation=cv2.INTER_AREA
                )
                logger.info(f"Resized image to: {new_width}x{new_height}")

            # Optimize image encoding with lower quality
            _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 70])
            image_bytes = buffer.tobytes()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            return image_b64, image.shape
        except Exception as e:
            logger.error(f"Error optimizing image: {str(e)}")
            return None, None

    def _make_api_call(self, image_b64: str) -> Dict[str, Any]:
        """Make API call with optimized parameters."""
        try:
            # Optimized prompt focusing on tax deduction essentials
            prompt = """Extract and structure the following receipt information in JSON format for tax deduction purposes.
            Focus on these essential details:
            - Store/Vendor name and TIN (Tax Identification Number)
            - Date and time of transaction
            - Items with quantities and prices
            - VAT amount (12%)
            - Discount amount
            - Payment method
            - Total amount
            
            Format the response as a JSON object with these fields:
            {
                "store_info": {
                    "name": "store/vendor name",
                    "tin": "TIN number if available"
                },
                "transaction_info": {
                    "date": "date in YYYY-MM-DD format",
                    "time": "time in HH:MM:SS format",
                    "payment_method": "payment method"
                },
                "items": [
                    {
                        "title": "item name",
                        "quantity": "quantity as integer",
                        "price": "price as decimal",
                        "subtotal": "quantity * price as decimal"
                    }
                ],
                "totals": {
                    "total_expediture": "total amount as decimal",
                    "value_added_tax": "VAT amount as decimal",
                    "discount": "discount amount as decimal"
                }
            }

            Important notes:
            1. All monetary values should be decimal numbers
            2. Quantities should be integers
            3. Focus on accuracy of financial data
            4. If any field is not found, use null
            """

            logger.info("Sending request to OpenAI Vision API...")
            response = client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=600,  # Further reduced for faster response
                temperature=0.1,
            )

            # Parse the response
            result = response.choices[0].message.content
            try:
                # Try to find JSON in the response
                json_str = re.search(r"\{.*\}", result, re.DOTALL)
                if json_str:
                    parsed_data = json.loads(json_str.group())
                    logger.info("Successfully extracted and parsed receipt data")
                    return {"success": True, "data": parsed_data, "raw_text": result}
                else:
                    logger.error("No JSON found in response")
                    return {"success": False, "error": "No JSON found in response"}
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                return {"success": False, "error": f"JSON parsing error: {str(e)}"}

        except Exception as e:
            logger.error(f"Error in API call: {str(e)}")
            return {"success": False, "error": str(e)}

    def extract_with_openai_vision(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text and parse receipt in a single API call."""
        try:
            # Check cache first
            image_hash = hash(image.tobytes())
            if image_hash in self._image_cache:
                logger.info("Using cached result")
                return self._image_cache[image_hash]

            # Optimize image
            image_b64, _ = self._optimize_image(image)
            if not image_b64:
                return {"success": False, "error": "Failed to optimize image"}

            # Make API call
            result = self._make_api_call(image_b64)

            # Cache successful results
            if result["success"]:
                self._image_cache[image_hash] = result
                # Limit cache size
                if len(self._image_cache) > 100:
                    self._image_cache.pop(next(iter(self._image_cache)))

            return result

        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            return {"success": False, "error": str(e)}

    def extract_text(self, image: np.ndarray) -> Dict[str, Any]:
        """Main method to extract text from image."""
        logger.info("Starting text extraction process...")
        return self.extract_with_openai_vision(image)
