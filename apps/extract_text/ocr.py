import cv2
import numpy as np
import pytesseract
from PIL import Image
import io

# If needed, set the tesseract command (adjust the path accordingly)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def preprocess_image(image):
    """
    Preprocess the image for better OCR results:
    - Convert to grayscale.
    - Apply thresholding.
    - Optionally, perform noise reduction or resizing.
    """
    # Convert image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply a simple threshold to get a binary image
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    return thresh


def extract_text_from_image(image_file):
    """
    Accepts an image file-like object, processes it, and extracts text.
    """
    try:
        # Read image file into memory using OpenCV
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        processed_img = preprocess_image(img)

        # Optional: Save or display processed image for debugging
        # cv2.imwrite("processed.png", processed_img)

        text = pytesseract.image_to_string(processed_img)

        return text
    except Exception as e:
        raise Exception("Error processing image: " + str(e))
