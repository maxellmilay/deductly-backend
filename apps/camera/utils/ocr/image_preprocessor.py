"""
Image preprocessing utilities for receipt OCR.
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Handles all image preprocessing operations for receipt OCR."""

    def __init__(self):
        self._cache_size = 100
        self._cache = {}

    def _get_image_hash(self, image: np.ndarray) -> str:
        """Generate a hash for the image to use as cache key."""
        return hashlib.md5(image.tobytes()).hexdigest()

    @staticmethod
    def detect_edges(image: np.ndarray) -> np.ndarray:
        """
        Simple edge detection that preserves more details.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Gentle blur to reduce noise while preserving edges
        blur = cv2.GaussianBlur(gray, (3, 3), 0)

        # Simple Canny edge detection with conservative thresholds
        edges = cv2.Canny(blur, 30, 100)

        return edges

    @staticmethod
    def find_receipt_contour(edges: np.ndarray) -> Optional[np.ndarray]:
        """Find the receipt contour in the edge-detected image."""
        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Filter contours by area
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:  # Skip small contours
                continue
            valid_contours.append(contour)

        if not valid_contours:
            return None

        return max(valid_contours, key=cv2.contourArea)

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Simple deskew using Hough Line Transform."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10
        )

        if lines is None:
            return image

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = np.arctan((y2 - y1) / (x2 - x1)) * 180 / np.pi
                angles.append(angle)

        if not angles:
            return image

        median_angle = np.median(angles)
        if abs(median_angle) < 5:  # Increased threshold from 1 to 5 degrees
            return image

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

        return rotated

    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """
        Enhanced preprocessing for OCR that preserves text details.
        """
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply adaptive thresholding to handle varying lighting conditions
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Denoise the image
        denoised = cv2.fastNlMeansDenoising(binary, h=10)

        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Add small border
        border_size = 10
        with_border = cv2.copyMakeBorder(
            enhanced,
            border_size,
            border_size,
            border_size,
            border_size,
            cv2.BORDER_CONSTANT,
            value=255,
        )

        return with_border

    @staticmethod
    def enhance_color_receipt(image: np.ndarray) -> np.ndarray:
        """
        Enhanced color receipt image for OCR, preserving color and gently improving contrast.
        Optimized for speed by reducing unnecessary operations.
        """
        # Convert to LAB color space for better contrast enhancement
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # CLAHE on the L channel with optimized parameters
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        # Merge back and convert to BGR
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # Add small white border
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

    @staticmethod
    def detect_skew_angle(image: np.ndarray) -> float:
        """
        Detect the skew angle of the image using Hough Line Transform.
        Returns angle in degrees.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10
        )
        if lines is None:
            return 0.0
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = np.arctan((y2 - y1) / (x2 - x1)) * 180 / np.pi
                angles.append(angle)
        if not angles:
            return 0.0
        median_angle = np.median(angles)
        return median_angle

    def process_image(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Improved processing pipeline for already-cropped, color receipts:
        - Only deskew if strong skew detected (>5 degrees)
        - Use color-preserving enhancement
        - Cached results for repeated processing
        """
        try:
            # Check cache first
            image_hash = self._get_image_hash(image)
            if image_hash in self._cache:
                return self._cache[image_hash]

            logger.info(f"Processing image with shape: {image.shape}")

            # Convert to grayscale for initial processing
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # Denoise
            denoised = cv2.fastNlMeansDenoising(binary, h=10)

            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # Add border
            border_size = 10
            with_border = cv2.copyMakeBorder(
                enhanced,
                border_size,
                border_size,
                border_size,
                border_size,
                cv2.BORDER_CONSTANT,
                value=255,
            )

            # Save debug image
            debug_path = "debug_preprocessed.jpg"
            cv2.imwrite(debug_path, with_border)
            logger.info(f"Saved debug image to {debug_path}")

            result = (with_border, True)

            # Cache the result
            if len(self._cache) >= self._cache_size:
                # Remove oldest item if cache is full
                self._cache.pop(next(iter(self._cache)))
            self._cache[image_hash] = result

            return result

        except Exception as e:
            logger.error(f"Error in image preprocessing: {str(e)}")
            return image, False
