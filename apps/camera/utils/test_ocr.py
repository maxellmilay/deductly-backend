import cv2
import numpy as np
import os
from ocr.receipt_processor import ReceiptProcessor
from ocr.image_preprocessor import ImagePreprocessor
from ocr.text_extractor import TextExtractor
from ocr.receipt_parser import ReceiptParser


def test_ocr_process(image_path):
    """
    Test the OCR process with a sample image.
    Shows the processed image and extracted text.
    """
    # Initialize processors
    processor = ReceiptProcessor()
    preprocessor = ImagePreprocessor()
    text_extractor = TextExtractor()
    receipt_parser = ReceiptParser()

    # Load image
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return

    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not load image")
        return

    print("\n=== Starting OCR Process ===")

    # 1. Preprocess image
    print("\n1. Preprocessing image...")
    processed_image, success = preprocessor.process_image(image)
    if not success:
        print("Warning: Image preprocessing may have issues")

    # Save processed image to test_images directory
    processed_path = os.path.join("test_images", "processed_receipt.jpg")
    cv2.imwrite(processed_path, processed_image)
    print(f"Processed image saved to: {processed_path}")

    # 2. Extract text
    print("\n2. Extracting text...")
    extraction_result = text_extractor.extract_text(
        processed_image, use_all_methods=True
    )

    print("\nExtracted Text:")
    print("-" * 50)
    print(extraction_result["best_text"])
    print("-" * 50)

    # 3. Parse receipt
    print("\n3. Parsing receipt...")
    parsed_data = receipt_parser.parse_receipt(extraction_result["best_text"])

    print("\nParsed Receipt Data:")
    print("-" * 50)
    print(f"Store Info: {parsed_data.get('store_info', {})}")
    print(f"Transaction Info: {parsed_data.get('transaction_info', {})}")
    print(f"Items: {parsed_data.get('items', [])}")
    print(f"Totals: {parsed_data.get('totals', {})}")
    print(f"Metadata: {parsed_data.get('metadata', {})}")
    print("-" * 50)

    # 4. Full pipeline test
    print("\n4. Testing full pipeline...")
    full_result = processor.process_receipt(
        image_data=image, use_all_ocr_methods=True, return_debug_info=True
    )

    print("\nFull Pipeline Result:")
    print("-" * 50)
    print(f"Success: {full_result['success']}")
    if not full_result["success"]:
        print(f"Error: {full_result['error']}")
    else:
        print("\nDebug Info:")
        print(f"Preprocessing: {full_result['debug_info'].get('preprocessing', {})}")
        print(
            f"Text Extraction: {full_result['debug_info'].get('text_extraction', {})}"
        )
        print(f"Raw Text: {full_result['debug_info'].get('raw_text', '')}")
    print("-" * 50)


if __name__ == "__main__":
    # Path to your receipt image in the test_images directory
    image_path = os.path.join("test_images", "receipt.jpg")
    test_ocr_process(image_path)
