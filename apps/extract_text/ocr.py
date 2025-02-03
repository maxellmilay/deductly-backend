import cv2
import numpy as np
import pytesseract
import imutils
from imutils.perspective import four_point_transform
from PIL import Image
import io

# If needed, set the tesseract command (adjust the path accordingly)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def preprocess_image(image):
    """
    Preprocess the image specifically for receipt OCR:
    - Resize for consistent processing
    - Convert to grayscale
    - Apply Gaussian blur
    - Detect edges
    - Find and transform receipt contours
    """
    # Create a copy and resize
    image_copy = image.copy()
    image_copy = imutils.resize(image_copy, width=500)
    ratio = image.shape[1] / float(image_copy.shape[1])

    # Convert to grayscale and apply Gaussian blur
    gray = cv2.cvtColor(image_copy, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Detect edges
    edged = cv2.Canny(blurred, 75, 200)

    # Find contours
    cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    # Find receipt contour
    receipt_cnt = None
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            receipt_cnt = approx
            break

    # If receipt contour found, transform perspective
    if receipt_cnt is not None:
        receipt = four_point_transform(image, receipt_cnt.reshape(4, 2) * ratio)
        return receipt

    # If no receipt contour found, return original image with basic processing
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return thresh


def extract_text_from_image(image_file):
    """
    Accepts an image file-like object, processes it specifically for receipts, and extracts text.
    """
    try:
        # Read image file into memory using OpenCV
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        processed_img = preprocess_image(img)

        # Configure Tesseract for receipt-specific OCR
        custom_config = "--psm 6"  # Assume uniform text block
        text = pytesseract.image_to_string(
            cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB), config=custom_config
        )

        return text
    except Exception as e:
        raise Exception("Error processing receipt image: " + str(e))
