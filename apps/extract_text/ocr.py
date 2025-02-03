import cv2
import numpy as np
import pytesseract
import io
import csv
import re
import os

# Tesseract path configuration
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def detect_and_crop_receipt(image):
    """
    Detect receipt edges and crop the image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply bilateral filter to reduce noise while keeping edges sharp
    blur = cv2.bilateralFilter(gray, 9, 75, 75)

    # Apply Canny edge detection
    edges = cv2.Canny(blur, 50, 150)

    # Dilate edges to connect any broken lines
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return image

    # Find the largest contour (should be the receipt)
    receipt_contour = max(contours, key=cv2.contourArea)

    # Get the minimum area rectangle
    rect = cv2.minAreaRect(receipt_contour)
    box = cv2.boxPoints(rect)
    box = np.int32(box)

    # Get width and height of the receipt
    width = int(rect[1][0])
    height = int(rect[1][1])

    # Source points
    src_pts = box.astype("float32")

    # Destination points
    dst_pts = np.array(
        [[0, height - 1], [0, 0], [width - 1, 0], [width - 1, height - 1]],
        dtype="float32",
    )

    # Get perspective transform matrix
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # Warp the image
    warped = cv2.warpPerspective(image, M, (width, height))

    return warped


def preprocess_for_ocr(image):
    """
    Simplified preprocessing optimized for clean receipt images
    """
    # Convert to grayscale if not already
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Resize to a larger height while maintaining aspect ratio
    height = 2000
    aspect_ratio = gray.shape[1] / gray.shape[0]
    width = int(height * aspect_ratio)
    resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

    # Simple binary thresholding
    _, binary = cv2.threshold(resized, 180, 255, cv2.THRESH_BINARY)

    # Add white border
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


def extract_text_from_image(image_file):
    """
    Main function to process receipt image and extract text
    """
    try:
        # Create processed_images directory if it doesn't exist
        debug_dir = os.path.join(os.path.dirname(__file__), "processed_images")
        os.makedirs(debug_dir, exist_ok=True)

        # Read image file
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if image is None:
            raise Exception("Failed to load image")

        # Preprocess the image
        processed = preprocess_for_ocr(image)

        # Save debug image to processed_images folder
        debug_path = os.path.join(debug_dir, "debug_processed.png")
        cv2.imwrite(debug_path, processed)

        # Configure Tesseract for receipt text
        custom_config = (
            "--psm 6 "  # Assume uniform block of text
            "--oem 3 "  # Use LSTM OCR Engine
            "-c tessedit_char_blacklist=@#$%^&*()_+=[]{}|\\<>~"
        )

        # Extract text
        text = pytesseract.image_to_string(processed, config=custom_config, lang="eng")

        # Clean up the text
        text = text.strip()

        if not text:
            raise Exception("No text could be extracted from the image")

        # Parse the text into structured data
        structured_data = parse_receipt_text(text)

        return text, structured_data

    except Exception as e:
        raise Exception(f"Error processing receipt image: {str(e)}")


def parse_receipt_text(text):
    """
    Parse receipt text into structured data
    """
    lines = text.split("\n")
    items = []

    # Match price formats: XX.XX or $XX.XX
    price_pattern = r"\$?\d+\.\d+"

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Find all prices in the line
        prices = re.findall(price_pattern, line)

        if prices:
            # Get the last price (usually the item price)
            price = prices[-1]
            # Get everything before the price as description
            description = line[: line.rfind(price)].strip()

            if description:
                items.append({"description": description, "price": price})
        else:
            # Keep non-price lines that might be important
            if len(line) > 3 and not line.isspace():
                items.append({"description": line, "price": ""})

    return items


def generate_csv(structured_data):
    """
    Generate CSV from structured data
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["description", "price"])
    writer.writeheader()

    for item in structured_data:
        if item["description"].strip():
            writer.writerow(
                {
                    "description": item["description"].strip(),
                    "price": item["price"].strip(),
                }
            )

    return output.getvalue()
