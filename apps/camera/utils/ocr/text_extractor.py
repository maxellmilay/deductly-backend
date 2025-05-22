"""
Text extraction utilities for receipt OCR using OpenAI Vision API.
"""

import os
from openai import OpenAI
from typing import Dict, Any
import numpy as np
from dotenv import load_dotenv
import cv2
import logging
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import cloudinary.uploader
import threading
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

# Create a thread pool for parallel processing
executor = ThreadPoolExecutor(
    max_workers=4
)  # Increased workers for parallel processing


class TextExtractor:
    """Handles text extraction from images using OpenAI Vision API."""

    def __init__(self):
        self._image_cache = {}  # Simple cache for processed images
        self._lock = threading.Lock()  # Thread-safe cache operations

    @staticmethod
    @lru_cache(maxsize=100)
    def _get_optimized_prompt() -> str:
        """Cache the prompt to avoid string operations."""
        return """Extract and structure the following receipt information in JSON format. 
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
                "branch": "branch name if available",
                "address": "store address"
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
                    "price": "price",
                    "subtotal": "subtotal",
                    "is_deductible": true/false,
                    "deductible_amount": "amount that can be deducted",
                    "category": "FOOD/TRANSPORTATION/ENTERTAINMENT/OTHER"
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
                "serial_number": "serial number if available",
                "transaction_category": "FOOD/TRANSPORTATION/ENTERTAINMENT/OTHER",
                "is_deductible": true/false,
                "deductible_amount": "total amount that can be deducted"
            }
        }

        For deductibility classification:
        1. FOOD: 
           - Business meals with clients: 50% deductible
           - Employee meals: 100% deductible
           - Personal meals: 0% deductible
        2. TRANSPORTATION:
           - Business travel: 100% deductible
           - Personal travel: 0% deductible
        3. ENTERTAINMENT:
           - Business entertainment: 50% deductible
           - Personal entertainment: 0% deductible
        4. OTHER:
           - Business expenses: 100% deductible
           - Personal expenses: 0% deductible

        Extract all text from this receipt and structure it according to the above format.
        For each item, determine if it's deductible based on the context and business purpose.
        """

    def _optimize_image(self, image: np.ndarray) -> tuple:
        """Optimize image for API with minimal processing."""
        try:
            # Optimize image size for API using fastest interpolation
            max_dimension = 1024
            height, width = image.shape[:2]

            if max(height, width) > max_dimension:
                scale = max_dimension / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                # Use INTER_NEAREST for fastest resizing - quality is sufficient for OCR
                image = cv2.resize(
                    image, (new_width, new_height), interpolation=cv2.INTER_NEAREST
                )
                logger.info(f"Resized image to: {new_width}x{new_height}")

            # Optimize image encoding with lower quality and faster compression
            # Use IMWRITE_JPEG_OPTIMIZE=1 for faster encoding
            _, buffer = cv2.imencode(
                ".jpg",
                image,
                [cv2.IMWRITE_JPEG_QUALITY, 70, cv2.IMWRITE_JPEG_OPTIMIZE, 1],
            )

            return buffer.tobytes(), image.shape
        except Exception as e:
            logger.error(f"Error optimizing image: {str(e)}")
            return None, None

    def _make_api_call(self, image_url: str) -> Dict[str, Any]:
        """Make API call with optimized parameters."""
        try:
            logger.info("Sending request to OpenAI Vision API...")
            response = client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._get_optimized_prompt()},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    }
                ],
                max_tokens=600,
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
            with self._lock:
                if image_hash in self._image_cache:
                    logger.info("Using cached result")
                    return self._image_cache[image_hash]

            # Optimize image and get buffer
            buffer, _ = self._optimize_image(image)
            if not buffer:
                return {"success": False, "error": "Failed to optimize image"}

            # Upload to Cloudinary and get URL
            result = cloudinary.uploader.upload(
                buffer,
                resource_type="image",
                format="jpg",
                folder="receipts/temp",
            )

            # Make API call
            api_result = self._make_api_call(result["secure_url"])

            # Cache successful results
            if api_result["success"]:
                with self._lock:
                    self._image_cache[image_hash] = api_result
                    # Limit cache size
                    if len(self._image_cache) > 100:
                        self._image_cache.pop(next(iter(self._image_cache)))

            return api_result

        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            return {"success": False, "error": str(e)}

    def extract_text(self, image: np.ndarray) -> Dict[str, Any]:
        """Main method to extract text from image."""
        logger.info("Starting text extraction process...")
        return self.extract_with_openai_vision(image)

    def save_to_database(
        self, extracted_data: Dict[str, Any], user_id: int, image_id: int
    ) -> Dict[str, Any]:
        """Save extracted receipt data to database."""
        try:
            from apps.receipt.models import Receipt, ReceiptItem, Vendor
            from apps.camera.models import Image
            from apps.account.models import CustomUser
            from decimal import Decimal

            # Get or create vendor
            vendor_data = extracted_data.get("store_info", {})
            vendor, _ = Vendor.objects.get_or_create(
                name=vendor_data.get("name", "Unknown Vendor"),
                defaults={
                    "address": vendor_data.get("address", ""),
                    "email": "",  # You might want to add this to the extraction
                    "contact_number": "",  # You might want to add this to the extraction
                    "establishment": vendor_data.get("branch", ""),
                },
            )

            # Create receipt
            totals = extracted_data.get("totals", {})
            metadata = extracted_data.get("metadata", {})

            receipt = Receipt.objects.create(
                title=f"Receipt from {vendor.name}",
                user_id=user_id,
                category=metadata.get("transaction_category", "OTHER"),
                image_id=image_id,
                total_expenditure=Decimal(str(totals.get("total", 0))),
                payment_method=extracted_data.get("transaction_info", {}).get(
                    "payment_method", "Unknown"
                ),
                vendor=vendor,
                discount=Decimal(str(totals.get("discount", 0))),
                value_added_tax=Decimal(str(totals.get("vat", 0))),
            )

            # Create receipt items
            for item_data in extracted_data.get("items", []):
                ReceiptItem.objects.create(
                    title=item_data.get("name", "Unknown Item"),
                    quantity=int(item_data.get("quantity", 1)),
                    price=Decimal(str(item_data.get("price", 0))),
                    subtotal_expenditure=Decimal(str(item_data.get("subtotal", 0))),
                    receipt=receipt,
                    deductable_amount=Decimal(
                        str(item_data.get("deductible_amount", 0))
                    ),
                )

            return {
                "success": True,
                "receipt_id": receipt.id,
                "message": "Receipt data saved successfully",
            }

        except Exception as e:
            logger.error(f"Error saving receipt data: {str(e)}")
            return {"success": False, "error": str(e)}
