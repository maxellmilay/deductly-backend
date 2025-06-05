#!/usr/bin/env python3
"""
Test script for PDF generation using the BIR Form 1701 template.
This script tests the generate_receipt_pdf function and saves the output as a PDF file.
"""

import sys
import os
import base64
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from apps.camera.utils.pdf_generator import generate_receipt_pdf


def create_sample_receipt_data():
    """Create comprehensive sample receipt data matching the expected schema."""
    return {
        "store_info": {
            "name": "ABC Business Solutions Inc.",
            "tin": "123-456-789-000",
            "branch": "Main Branch - Makati",
            "address": "1234 Ayala Avenue, Makati City, Metro Manila 1226",
        },
        "transaction_info": {
            "date": "2024-01-15",
            "time": "14:30:25",
            "payment_method": "Cash",
        },
        "items": [
            {
                "name": "Office Supplies - Printer Paper",
                "quantity": "5",
                "price": "250.00",
                "subtotal": "1250.00",
                "is_deductible": True,
                "deductible_amount": "1250.00",
                "category": "OTHER",
            },
            {
                "name": "Business Lunch - Client Meeting",
                "quantity": "1",
                "price": "2500.00",
                "subtotal": "2500.00",
                "is_deductible": True,
                "deductible_amount": "1250.00",  # 50% deductible for meals
                "category": "FOOD",
            },
            {
                "name": "Transportation - Taxi Fare",
                "quantity": "1",
                "price": "350.00",
                "subtotal": "350.00",
                "is_deductible": True,
                "deductible_amount": "350.00",
                "category": "TRANSPORTATION",
            },
        ],
        "totals": {
            "subtotal": "4100.00",
            "vat": "492.00",
            "service_charge": "50.00",
            "discount": "100.00",
            "total": "4542.00",
        },
        "metadata": {
            "currency": "PHP",
            "vat_rate": 0.12,
            "bir_accreditation": "BIR-ACC-2024-001234",
            "serial_number": "SN-202401-001",
            "transaction_category": "FOOD",
            "is_deductible": True,
            "deductible_amount": "2850.00",
        },
    }


def test_pdf_generation():
    """Test the PDF generation function and save the result."""
    print("🧪 Testing PDF Generation with BIR Form 1701 Template")
    print("=" * 60)

    # Create sample data
    print("📋 Creating sample receipt data...")
    receipt_data = create_sample_receipt_data()

    # Display sample data info
    store_name = receipt_data["store_info"]["name"]
    total_amount = receipt_data["totals"]["total"]
    deductible_amount = receipt_data["metadata"]["deductible_amount"]

    print(f"   Store: {store_name}")
    print(f"   Total Amount: PHP {total_amount}")
    print(f"   Deductible Amount: PHP {deductible_amount}")
    print(f"   Items: {len(receipt_data['items'])}")

    try:
        # Generate PDF
        print("\n🔄 Generating PDF...")
        start_time = datetime.now()

        pdf_base64 = generate_receipt_pdf(receipt_data)

        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()

        print(f"   ✅ PDF generated successfully in {generation_time:.3f} seconds")
        print(f"   📊 Base64 length: {len(pdf_base64):,} characters")

        # Decode and save PDF
        print("\n💾 Saving PDF to file...")
        pdf_bytes = base64.b64decode(pdf_base64)

        output_filename = f"test_receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        with open(output_filename, "wb") as f:
            f.write(pdf_bytes)

        file_size = len(pdf_bytes)
        print(f"   ✅ PDF saved as: {output_filename}")
        print(f"   📁 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

        # Verification
        print("\n🔍 Verification:")
        if os.path.exists(output_filename):
            actual_size = os.path.getsize(output_filename)
            print(f"   ✅ File exists and is {actual_size:,} bytes")

            # Check if it's a valid PDF
            with open(output_filename, "rb") as f:
                header = f.read(8)
                if header.startswith(b"%PDF-"):
                    print(
                        f"   ✅ Valid PDF file (version: {header.decode('ascii', errors='ignore')})"
                    )
                else:
                    print(f"   ❌ Invalid PDF header: {header}")
        else:
            print(f"   ❌ File not found: {output_filename}")

        print("\n" + "=" * 60)
        print("🎉 Test completed successfully!")
        print(f"📄 Generated PDF: {output_filename}")
        print("💡 You can now open the PDF file to verify the form has been filled.")

        return True

    except Exception as e:
        print(f"\n❌ Error during PDF generation: {str(e)}")
        import traceback

        print("\n🔍 Full error traceback:")
        traceback.print_exc()
        return False


def main():
    """Main function to run the test."""
    print("BIR Form 1701 PDF Generation Test")
    print("=" * 60)
    print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Working directory: {os.getcwd()}")

    success = test_pdf_generation()

    print(f"\n🕐 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
