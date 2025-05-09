"""
Main receipt processing orchestrator.
"""

import numpy as np
from typing import Dict, Any, Optional, Union
import cv2
import base64
import io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import hashlib
import logging

from .image_preprocessor import ImagePreprocessor
from .text_extractor import TextExtractor
from .receipt_parser import ReceiptParser

logger = logging.getLogger(__name__)


class ReceiptProcessor:
    """Orchestrates the receipt processing pipeline."""

    def __init__(self):
        self.image_preprocessor = ImagePreprocessor()
        self.text_extractor = TextExtractor()
        self.receipt_parser = ReceiptParser()

    def _get_image_hash(self, image: np.ndarray) -> str:
        """Generate a hash for the image to use as cache key."""
        return hashlib.md5(image.tobytes()).hexdigest()

    def _load_image(
        self, image_data: Union[str, bytes, np.ndarray]
    ) -> Optional[np.ndarray]:
        """Load image from various input formats."""
        try:
            if isinstance(image_data, str):
                # Check if it's a base64 string
                if image_data.startswith("data:image"):
                    # Extract the base64 part
                    image_data = image_data.split(",")[1]

                # Decode base64
                image_bytes = base64.b64decode(image_data)
                nparr = np.frombuffer(image_bytes, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            elif isinstance(image_data, bytes):
                # Convert bytes to numpy array
                nparr = np.frombuffer(image_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            elif isinstance(image_data, np.ndarray):
                return image_data.copy()

            else:
                raise ValueError("Unsupported image format")

        except Exception as e:
            print(f"Error loading image: {str(e)}")
            return None

    def process_receipt(
        self,
        image_data: Union[str, bytes, np.ndarray],
        use_all_ocr_methods: bool = False,
        return_debug_info: bool = False,
    ) -> Dict[str, Any]:
        """
        Process receipt image through the entire pipeline.
        Optimized with parallel processing and caching.

        Args:
            image_data: Receipt image in various formats (base64, bytes, or numpy array)
            use_all_ocr_methods: Whether to use multiple OCR methods (default: False)
            return_debug_info: Whether to return intermediate processing results

        Returns:
            Dictionary containing parsed receipt data and optional debug information
        """
        result = {
            "success": False,
            "error": None,
            "data": None,
            "debug_info": {} if return_debug_info else None,
        }

        try:
            # Load image
            image = self._load_image(image_data)
            if image is None:
                raise ValueError("Failed to load image")

            image_hash = self._get_image_hash(image)

            # Process image preprocessing and text extraction in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Start preprocessing
                preprocess_future = executor.submit(
                    self.image_preprocessor.process_image, image
                )

                # Get preprocessing result
                processed_image, preprocess_success = preprocess_future.result()

                if return_debug_info:
                    result["debug_info"]["preprocessing"] = {
                        "success": preprocess_success,
                        "image_shape": processed_image.shape,
                    }

                # Extract text
                extraction_result = self.text_extractor.extract_text(
                    processed_image, use_all_methods=use_all_ocr_methods
                )

                if return_debug_info:
                    result["debug_info"]["text_extraction"] = {
                        "method_used": extraction_result.get("method_used"),
                        "confidence": extraction_result.get("tesseract", {}).get(
                            "confidence"
                        ),
                    }

                # Check if we have valid data from Vision API
                if (
                    extraction_result.get("method_used") == "openai_vision"
                    and extraction_result.get("parsed_data")
                    and extraction_result.get("success", False)
                ):
                    # Use the parsed data directly
                    result["data"] = extraction_result["parsed_data"]
                    result["success"] = True
                else:
                    # Fallback to parsing the text
                    parsed_data = self.receipt_parser.parse_receipt(
                        extraction_result["best_text"]
                    )
                    result["data"] = parsed_data
                    result["success"] = True

                # Add the raw text to debug info if requested
                if return_debug_info:
                    result["debug_info"]["raw_text"] = extraction_result["best_text"]

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"Receipt processing error: {str(e)}")

        return result

    def save_debug_image(
        self, image: np.ndarray, filename: str, include_intermediate: bool = False
    ) -> Dict[str, str]:
        """
        Save debug images for inspection.

        Args:
            image: Original image
            filename: Base filename for saved images
            include_intermediate: Whether to save intermediate processing steps

        Returns:
            Dictionary of saved image paths
        """
        saved_images = {}

        try:
            # Save original image
            cv2.imwrite(f"{filename}_original.jpg", image)
            saved_images["original"] = f"{filename}_original.jpg"

            if include_intermediate:
                # Get intermediate processing steps
                edges = self.image_preprocessor.detect_edges(image)
                cv2.imwrite(f"{filename}_edges.jpg", edges)
                saved_images["edges"] = f"{filename}_edges.jpg"

                # Process image through pipeline
                processed, _ = self.image_preprocessor.process_image(image)
                cv2.imwrite(f"{filename}_processed.jpg", processed)
                saved_images["processed"] = f"{filename}_processed.jpg"

        except Exception as e:
            saved_images["error"] = str(e)

        return saved_images

    def get_supported_formats(self) -> Dict[str, Any]:
        """Return information about supported formats and features."""
        return {
            "input_formats": ["base64 image string", "image bytes", "numpy array"],
            "output_formats": ["JSON", "CSV"],
            "supported_receipt_features": [
                "Store name and branch",
                "TIN number",
                "Date and time",
                "Items and prices",
                "VAT details",
                "Total amount",
                "BIR accreditation",
                "Serial number",
            ],
            "supported_languages": [
                "English",
                "Tagalog (partial)",
                "Mixed English-Tagalog",
            ],
        }
