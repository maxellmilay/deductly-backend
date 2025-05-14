"""
Main receipt processing orchestrator.
"""

import numpy as np
from typing import Dict, Any, Optional, Union
import cv2
import base64
import io
from PIL import Image
import logging

from .image_preprocessor import ImagePreprocessor
from .text_extractor import TextExtractor

logger = logging.getLogger(__name__)


class ReceiptProcessor:
    """Orchestrates the receipt processing pipeline."""

    def __init__(self):
        self.image_preprocessor = ImagePreprocessor()
        self.text_extractor = TextExtractor()

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
            logger.error(f"Error loading image: {str(e)}")
            return None

    def process_receipt(
        self,
        image_data: Union[str, bytes, np.ndarray],
        return_debug_info: bool = False,
    ) -> Dict[str, Any]:
        """
        Process receipt image through the entire pipeline.

        Args:
            image_data: Receipt image in various formats (base64, bytes, or numpy array)
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

            # Preprocess image
            processed_image, preprocess_success = self.image_preprocessor.process_image(
                image
            )

            if return_debug_info:
                result["debug_info"]["preprocessing"] = {
                    "success": preprocess_success,
                    "image_shape": processed_image.shape,
                }

            # Extract text and parse receipt in one step
            extraction_result = self.text_extractor.extract_text(processed_image)

            if not extraction_result["success"]:
                raise ValueError(
                    f"Text extraction failed: {extraction_result.get('error')}"
                )

            # Set success result
            result["success"] = True
            result["data"] = extraction_result["data"]

            if return_debug_info:
                result["debug_info"]["raw_text"] = extraction_result.get("raw_text", "")

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

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
