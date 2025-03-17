import cv2
import numpy as np
import pytesseract
import io
import csv
import re
import os
import json
from openai import OpenAI
from datetime import datetime

# Tesseract path configuration
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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


def process_text_with_gpt(text):
    """
    Use GPT to extract structured information from receipt text
    """
    # Define the template structure separately
    template = {
        "store_info": {
            "name": "Store/Branch name",
            "address": "Full address on single line",
            "phone": "Phone number",
            "store_hours": "Operating hours in proper AM/PM format",
        },
        "transaction_info": {
            "date": "YYYY-MM-DD",
            "time": "HH:MM:SS",
            "receipt_id": "Full receipt/transaction/sequence number",
            "terminal_id": "Terminal/register ID if present",
            "payment_details": {
                "method": "Payment method",
                "card_type": "Card type if present",
                "auth_code": "Authorization code",
            },
        },
        "items": [
            {
                "description": "Item description",
                "quantity": "Numeric quantity",
                "unit_price": "Price per unit",
                "total_price": "Total price for item",
            }
        ],
        "totals": {
            "subtotal": "Subtotal amount",
            "tax": "Tax amount",
            "total": "Final total amount",
        },
    }

    instructions = """
1. Store Information:
   - Look for store name at the top of the receipt
   - Format address as a single line, separated by commas
   - Convert store hours to proper AM/PM format
   - Extract phone number in consistent format

2. Transaction Details:
   - Format date as YYYY-MM-DD
   - Extract full transaction/sequence number (look for SEQ, TID, etc.)
   - For card transactions, mask card numbers but preserve type
   - Include authorization codes

3. Items:
   - Separate quantity and unit price
   - Include item descriptions exactly as shown
   - Preserve all price information
   - Note any special codes or modifiers

4. Payment Information:
   - Identify payment method (DEBIT/CREDIT/CASH)
   - Include any card-specific details
   - Note authorization numbers
   - Include terminal/register IDs
"""

    # Combine everything into the prompt
    prompt = f"""Analyze this receipt text and extract information into a structured format.

{instructions}

Format the response as JSON matching this structure:
{json.dumps(template, indent=2)}

Receipt text to analyze:
{text}

Important:
- Preserve all original values and numbers
- Format addresses on a single line with proper commas
- Convert any 24-hour times to 12-hour format
- Keep all transaction and reference numbers
- If any field is not found, use null instead of making up values"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise receipt data extraction assistant. Extract and categorize all receipt information exactly as it appears, maintaining original values and proper formatting.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        # Parse the response
        parsed_data = json.loads(response.choices[0].message.content)
        return parsed_data
    except Exception as e:
        print(f"Error processing with GPT: {str(e)}")
        return None


def parse_receipt_text(text):
    """
    Parse receipt text into structured data using GPT
    """
    # First, use GPT to extract structured information
    structured_data = process_text_with_gpt(text)

    if not structured_data:
        # Fallback to basic parsing if GPT fails
        items = []
        lines = text.split("\n")
        price_pattern = r"\$?\d+\.\d+"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            prices = re.findall(price_pattern, line)
            if prices:
                price = prices[-1]
                description = line[: line.rfind(price)].strip()
                if description:
                    items.append({"description": description, "price": price})
            else:
                if len(line) > 3 and not line.isspace():
                    items.append({"description": line, "price": ""})

        return {"items": items}

    return structured_data


def generate_csv(structured_data):
    """
    Generate CSV from structured data with enhanced formatting and categorization
    """
    output = io.StringIO()
    fieldnames = [
        "Category",
        "Description",
        "Amount",
        "Date",
        "Store",
        "Receipt ID",
        "Payment Method",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    # Write store information
    if "store_info" in structured_data:
        store_info = structured_data["store_info"]
        # Store name and basic info
        if store_info.get("name"):
            writer.writerow(
                {
                    "Category": "Store Name",
                    "Description": store_info["name"],
                    "Amount": "",
                    "Date": structured_data.get("transaction_info", {}).get("date", ""),
                    "Store": store_info["name"],
                    "Receipt ID": structured_data.get("transaction_info", {}).get(
                        "receipt_id", ""
                    ),
                    "Payment Method": structured_data.get("transaction_info", {})
                    .get("payment_details", {})
                    .get("method", ""),
                }
            )

        # Store address - ensure it's on one line
        if store_info.get("address"):
            writer.writerow(
                {
                    "Category": "Store Address",
                    "Description": store_info["address"].replace("\n", ", "),
                    "Amount": "",
                    "Date": structured_data.get("transaction_info", {}).get("date", ""),
                    "Store": store_info.get("name", ""),
                    "Receipt ID": structured_data.get("transaction_info", {}).get(
                        "receipt_id", ""
                    ),
                    "Payment Method": "",
                }
            )

        # Store hours
        if store_info.get("store_hours"):
            writer.writerow(
                {
                    "Category": "Store Hours",
                    "Description": store_info["store_hours"],
                    "Amount": "",
                    "Date": structured_data.get("transaction_info", {}).get("date", ""),
                    "Store": store_info.get("name", ""),
                    "Receipt ID": structured_data.get("transaction_info", {}).get(
                        "receipt_id", ""
                    ),
                    "Payment Method": "",
                }
            )

    # Write transaction details
    if "transaction_info" in structured_data:
        trans_info = structured_data["transaction_info"]
        payment_details = trans_info.get("payment_details", {})

        # Terminal/Register ID if present
        if trans_info.get("terminal_id"):
            writer.writerow(
                {
                    "Category": "Terminal ID",
                    "Description": f"Terminal: {trans_info['terminal_id']}",
                    "Amount": "",
                    "Date": trans_info.get("date", ""),
                    "Store": structured_data.get("store_info", {}).get("name", ""),
                    "Receipt ID": trans_info.get("receipt_id", ""),
                    "Payment Method": "",
                }
            )

        # Payment information
        if payment_details:
            payment_desc = []
            if payment_details.get("method"):
                payment_desc.append(payment_details["method"])
            if payment_details.get("card_type"):
                payment_desc.append(payment_details["card_type"])

            writer.writerow(
                {
                    "Category": "Payment Details",
                    "Description": " ".join(payment_desc),
                    "Amount": "",
                    "Date": trans_info.get("date", ""),
                    "Store": structured_data.get("store_info", {}).get("name", ""),
                    "Receipt ID": trans_info.get("receipt_id", ""),
                    "Payment Method": payment_details.get("method", ""),
                }
            )

            # Authorization info if present
            if payment_details.get("auth_code"):
                writer.writerow(
                    {
                        "Category": "Authorization",
                        "Description": f"Auth Code: {payment_details['auth_code']}",
                        "Amount": "",
                        "Date": trans_info.get("date", ""),
                        "Store": structured_data.get("store_info", {}).get("name", ""),
                        "Receipt ID": trans_info.get("receipt_id", ""),
                        "Payment Method": payment_details.get("method", ""),
                    }
                )

    # Write items
    if "items" in structured_data:
        for item in structured_data["items"]:
            if isinstance(item, dict):
                qty = item.get("quantity", "")
                desc = item.get("description", "").strip()
                unit_price = item.get("unit_price", "")
                total_price = item.get("total_price", "")

                # Format description with quantity and unit price if available
                full_desc = []
                if qty:
                    full_desc.append(f"Qty: {qty}")
                full_desc.append(desc)
                if unit_price and unit_price != total_price:
                    full_desc.append(f"@ {unit_price} each")

                writer.writerow(
                    {
                        "Category": "Item",
                        "Description": " ".join(full_desc),
                        "Amount": total_price,
                        "Date": structured_data.get("transaction_info", {}).get(
                            "date", ""
                        ),
                        "Store": structured_data.get("store_info", {}).get("name", ""),
                        "Receipt ID": structured_data.get("transaction_info", {}).get(
                            "receipt_id", ""
                        ),
                        "Payment Method": structured_data.get("transaction_info", {})
                        .get("payment_details", {})
                        .get("method", ""),
                    }
                )

    # Write totals
    if "totals" in structured_data:
        totals = structured_data["totals"]

        # Subtotal if present
        if totals.get("subtotal"):
            writer.writerow(
                {
                    "Category": "Subtotal",
                    "Description": "Subtotal",
                    "Amount": totals["subtotal"],
                    "Date": structured_data.get("transaction_info", {}).get("date", ""),
                    "Store": structured_data.get("store_info", {}).get("name", ""),
                    "Receipt ID": structured_data.get("transaction_info", {}).get(
                        "receipt_id", ""
                    ),
                    "Payment Method": structured_data.get("transaction_info", {})
                    .get("payment_details", {})
                    .get("method", ""),
                }
            )

        # Tax if present
        if totals.get("tax"):
            writer.writerow(
                {
                    "Category": "Tax",
                    "Description": "Sales Tax",
                    "Amount": totals["tax"],
                    "Date": structured_data.get("transaction_info", {}).get("date", ""),
                    "Store": structured_data.get("store_info", {}).get("name", ""),
                    "Receipt ID": structured_data.get("transaction_info", {}).get(
                        "receipt_id", ""
                    ),
                    "Payment Method": structured_data.get("transaction_info", {})
                    .get("payment_details", {})
                    .get("method", ""),
                }
            )

        # Total
        if totals.get("total"):
            writer.writerow(
                {
                    "Category": "Total",
                    "Description": "Total Amount",
                    "Amount": totals["total"],
                    "Date": structured_data.get("transaction_info", {}).get("date", ""),
                    "Store": structured_data.get("store_info", {}).get("name", ""),
                    "Receipt ID": structured_data.get("transaction_info", {}).get(
                        "receipt_id", ""
                    ),
                    "Payment Method": structured_data.get("transaction_info", {})
                    .get("payment_details", {})
                    .get("method", ""),
                }
            )

    return output.getvalue()
