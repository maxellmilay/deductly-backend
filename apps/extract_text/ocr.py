import cv2
import numpy as np
import pytesseract
import imutils
from imutils.perspective import four_point_transform
from PIL import Image
import io
import csv
import re

# If needed, set the tesseract command (adjust the path accordingly)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def preprocess_image(image):
    """
    Enhanced preprocessing for receipt OCR
    """
    # Create a copy and resize while maintaining aspect ratio
    height = 1800  # Target height for better OCR
    aspect = image.shape[0] / image.shape[1]
    width = int(height / aspect)
    image_copy = cv2.resize(image, (width, height))

    # Convert to grayscale
    gray = cv2.cvtColor(image_copy, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )

    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh)

    return denoised


def parse_receipt_text(text):
    """
    Enhanced parsing of receipt text with better price detection
    """
    lines = text.split("\n")
    items = []

    # Common price patterns in receipts
    price_pattern = r"\$?\d+\.\d{2}\b"  # Matches prices like $12.34 or 12.34

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for price at the end of the line
        price_matches = list(re.finditer(price_pattern, line))
        if price_matches:
            # Get the last price in the line (usually the item price)
            price_match = price_matches[-1]
            price = price_match.group()

            # Get description (everything before the price)
            description = line[: price_match.start()].strip()

            # Clean up the description
            description = re.sub(r"\s+", " ", description)  # Remove extra spaces
            description = description.strip(".- ")  # Remove common separators

            if description:  # Only add if we have a description
                items.append({"description": description, "price": price})
        else:
            # Store lines without prices if they look meaningful
            line = re.sub(r"\s+", " ", line).strip()
            if len(line) > 1 and not line.isspace():  # Skip very short or empty lines
                items.append({"description": line, "price": ""})

    return items


def extract_text_from_image(image_file):
    """
    Enhanced text extraction with better OCR configuration
    """
    try:
        # Read image file into memory using OpenCV
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            raise Exception("Failed to load image")

        processed_img = preprocess_image(img)

        # Configure Tesseract with better parameters for receipt OCR
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!@#$%^&*()_+-=\/ "'

        text = pytesseract.image_to_string(
            processed_img,
            config=custom_config,
            lang="eng",  # Ensure English language is used
        )

        # Clean up the extracted text
        text = text.replace("|", "I")  # Common OCR mistake
        text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)  # Remove control characters

        # Parse the text into structured data
        structured_data = parse_receipt_text(text)

        # Don't return empty results
        if not text.strip() or not structured_data:
            raise Exception("No text could be extracted from the image")

        return text, structured_data
    except Exception as e:
        raise Exception(f"Error processing receipt image: {str(e)}")


def generate_csv(structured_data):
    """
    Generate CSV with better formatting
    """
    if not structured_data:
        return "description,price\n"  # Return header only if no data

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["description", "price"])
    writer.writeheader()

    # Filter out empty rows and clean data
    for item in structured_data:
        if item["description"].strip():  # Only write rows with descriptions
            cleaned_item = {
                "description": item["description"].strip(),
                "price": item["price"].strip(),
            }
            writer.writerow(cleaned_item)

    return output.getvalue()
