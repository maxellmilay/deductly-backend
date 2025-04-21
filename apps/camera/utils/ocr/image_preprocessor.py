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
        Detect edges in the image using advanced edge detection.
        Optimized for Philippine receipt formats.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.bilateralFilter(gray, 9, 75, 75)

        # Use adaptive thresholding for better edge detection in varying lighting
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Multiple edge detection methods for better accuracy
        edges_canny = cv2.Canny(thresh, 50, 150)
        edges_sobel_x = cv2.Sobel(thresh, cv2.CV_64F, 1, 0, ksize=3)
        edges_sobel_y = cv2.Sobel(thresh, cv2.CV_64F, 0, 1, ksize=3)

        # Combine edge detection results
        edges = cv2.addWeighted(
            np.absolute(edges_sobel_x), 0.5, np.absolute(edges_sobel_y), 0.5, 0
        )
        edges = np.uint8(edges)
        edges = cv2.addWeighted(edges, 0.5, edges_canny, 0.5, 0)

        return edges

    @staticmethod
    def find_receipt_contour(edges: np.ndarray) -> Optional[np.ndarray]:
        """Find the receipt contour in the edge-detected image."""
        # Dilate edges to connect broken lines
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Filter contours by area and aspect ratio
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:  # Skip small contours
                continue

            # Check aspect ratio
            _, _, w, h = cv2.boundingRect(contour)
            aspect_ratio = h / w if w > 0 else 0
            if 1.5 <= aspect_ratio <= 6.0:  # Common receipt aspect ratios
                valid_contours.append(contour)

        if not valid_contours:
            return None

        return max(valid_contours, key=cv2.contourArea)

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Deskew the image using Hough Line Transform."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Use probabilistic Hough Line Transform
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

        # Get median angle to avoid outliers
        median_angle = np.median(angles)

        # Rotate image
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
        Enhance image for better OCR results.
        Specifically tuned for Philippine receipt formats and common printers.
        """
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Denoise while preserving text edges
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

        # Adaptive thresholding for better text separation
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Add border for better OCR
        border_size = 20
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

    def process_image(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Main processing pipeline for receipt images.
        Returns processed image and success flag.
        """
        try:
            # Detect edges
            edges = self.detect_edges(image)

            # Find receipt contour
            contour = self.find_receipt_contour(edges)
            if contour is None:
                # If no contour found, proceed with full image
                processed = image
            else:
                # Create mask and extract receipt
                mask = np.zeros_like(image)
                cv2.drawContours(mask, [contour], -1, (255, 255, 255), -1)
                processed = cv2.bitwise_and(image, mask)

            # Deskew image
            deskewed = self.deskew(processed)

            # Enhance for OCR
            enhanced = self.enhance_for_ocr(deskewed)

            return enhanced, True

        except Exception as e:
            print(f"Error in image preprocessing: {str(e)}")
            return image, False
