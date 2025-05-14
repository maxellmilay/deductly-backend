"""
Image preprocessing utilities for receipt OCR.
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Handles image enhancement for OCR."""

    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """Optimized enhancement for OCR that preserves text details."""
        try:
            # Optimize image size for OCR
            height, width = image.shape[:2]
            if width > 1000:
                scale = 1000 / width
                new_width = 1000
                new_height = int(height * scale)
                image = cv2.resize(
                    image, (new_width, new_height), interpolation=cv2.INTER_AREA
                )
                logger.info(f"Resized image to: {new_width}x{new_height}")

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Gentle contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Light denoising
            denoised = cv2.fastNlMeansDenoising(enhanced, h=7)

            # Adaptive thresholding with gentle parameters
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3
            )

            # Add small border
            border_size = 10
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
            # Optimize image size
            height, width = image.shape[:2]
            if width > 1000:
                scale = 1000 / width
                new_width = 1000
                new_height = int(height * scale)
                image = cv2.resize(
                    image, (new_width, new_height), interpolation=cv2.INTER_AREA
                )
                logger.info(f"Resized image to: {new_width}x{new_height}")

            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # CLAHE on the L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)

            # Merge back and convert to BGR
            limg = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

            # Gentle denoising
            enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 5, 5, 7, 21)

            # Add a small white border
            border_size = 10
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
            # First try color enhancement
            enhanced = self.enhance_color_receipt(image)

            # If color enhancement fails, try grayscale enhancement
            if enhanced is None or enhanced.size == 0:
                enhanced = self.enhance_for_ocr(image)

            return enhanced, True
        except Exception as e:
            logger.error(f"Error in image processing: {str(e)}")
            return image, False
