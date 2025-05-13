"""
Image preprocessing utilities for receipt OCR.
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class ImagePreprocessor:
    """Handles all image preprocessing operations for receipt OCR."""

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
        if abs(median_angle) < 1:  # Skip small rotations
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
        Gentle enhancement for OCR that preserves text details.
        """
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

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

    @staticmethod
    def enhance_color_receipt(image: np.ndarray) -> np.ndarray:
        """
        Enhance a color receipt image for OCR, preserving color and gently improving contrast.
        """
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

    @staticmethod
    def detect_skew_angle(image: np.ndarray) -> float:
        """
        Detect the skew angle of the image using Hough Line Transform. Returns angle in degrees.
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

    def process_image(self, image: np.ndarray) -> tuple:
        """
        Only apply color/contrast enhancement for AI OCR. No cropping or deskewing.
        """
        try:
            enhanced = self.enhance_color_receipt(image)
            return enhanced, True
        except Exception as e:
            print(f"Error in image preprocessing: {str(e)}")
            return image, False
