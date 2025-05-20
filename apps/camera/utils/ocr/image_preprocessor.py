"""
Image preprocessing utilities for receipt OCR.
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Handles image enhancement for OCR."""

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_clahe():
        """Cache CLAHE object to avoid recreation."""
        return cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4))

    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """Optimized enhancement for OCR that preserves text details."""
        try:
            # Convert to grayscale - using faster method
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Use cached CLAHE
            clahe = ImagePreprocessor._get_clahe()
            enhanced = clahe.apply(gray)

            # Skip denoising for speed - OCR can handle some noise
            # Faster thresholding with optimized block size
            binary = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # Smaller border for faster processing
            border_size = 5
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
        except Exception as e:
            logger.error(f"Error in image enhancement: {str(e)}")
            return image

    @staticmethod
    def enhance_color_receipt(image: np.ndarray) -> np.ndarray:
        """Optimized color receipt enhancement for OCR."""
        try:
            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Use cached CLAHE
            clahe = ImagePreprocessor._get_clahe()
            cl = clahe.apply(l)

            # Merge back and convert to BGR
            limg = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

            # Skip denoising for speed - OCR can handle some noise
            # Smaller border for faster processing
            border_size = 5
            with_border = cv2.copyMakeBorder(
                enhanced,
                border_size,
                border_size,
                border_size,
                border_size,
                cv2.BORDER_CONSTANT,
                value=[255, 255, 255],
            )

            return with_border
        except Exception as e:
            logger.error(f"Error in color enhancement: {str(e)}")
            return image

    def process_image(self, image: np.ndarray) -> tuple:
        """Main method to process image for OCR."""
        try:
            # Try color enhancement first
            enhanced = self.enhance_color_receipt(image)

            # If color enhancement fails, try grayscale enhancement
            if enhanced is None or enhanced.size == 0:
                enhanced = self.enhance_for_ocr(image)

            return enhanced, True
        except Exception as e:
            logger.error(f"Error in image processing: {str(e)}")
            return image, False
