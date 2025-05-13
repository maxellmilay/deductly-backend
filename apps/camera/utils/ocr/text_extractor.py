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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))


class TextExtractor:
    """Handles text extraction from images using OpenAI Vision API."""

    def __init__(self):
        pass

    def extract_with_openai_vision(self, image: np.ndarray) -> Dict[str, Any]:
        """Optimized text extraction using OpenAI Vision API with Philippine context."""
        try:
            # Optimize image size before encoding to reduce API payload
            max_dimension = 1024  # Maximum dimension for the image
            height, width = image.shape[:2]

            logger.info(f"Original image size: {width}x{height}")

            if max(height, width) > max_dimension:
                scale = max_dimension / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(
                    image, (new_width, new_height), interpolation=cv2.INTER_AREA
                )
                logger.info(f"Resized image to: {new_width}x{new_height}")

            # Convert image to bytes with optimized compression
            _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            image_bytes = buffer.tobytes()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            logger.info("Image encoded successfully")

            # Streamlined prompt for faster processing
            prompt = """
            Extract all text from this Philippine receipt. Focus on:
            1. Store name, location, TIN
            2. Date, receipt number
            3. Items, quantities, prices
            4. Subtotal, VAT, total amount
            5. Payment method
            Format clearly, preserve layout, include all numbers and special characters.
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
                max_tokens=1000,  # Reduced token limit for faster response
                temperature=0.1,
            )

            extracted_text = response.choices[0].message.content
            logger.info(
                f"Successfully extracted text: {len(extracted_text)} characters"
            )

            return {
                "text": extracted_text,
                "model": "gpt-4.1-nano",
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            return {"text": "", "error": str(e), "success": False}

    def extract_text(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract text using OpenAI Vision API.
        """
        logger.info("Starting text extraction process...")
        result = self.extract_with_openai_vision(image)

        if not result["success"]:
            logger.error(
                f"Text extraction failed: {result.get('error', 'Unknown error')}"
            )
        else:
            logger.info("Text extraction completed successfully")

        return {
            "best_text": result.get("text", ""),
            "method_used": "openai_vision",
            "success": result.get("success", False),
            "error": result.get("error", None),
        }
