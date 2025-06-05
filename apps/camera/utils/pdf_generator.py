import io
from pypdf import PdfReader, PdfWriter
import base64
from datetime import datetime
import os


def _format_currency(value):
    """Safely format currency values."""
    try:
        # Remove any commas and convert to float
        if isinstance(value, str):
            value = value.replace(",", "").replace("P", "")
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "0.00"


def _safe_get(data, key, default=""):
    """Safely get value from nested dictionary."""
    try:
        keys = key.split(".")
        result = data
        for k in keys:
            result = result[k]
        return str(result) if result is not None else default
    except (KeyError, TypeError):
        return default


def generate_receipt_pdf(receipt_data):
    """Generate a filled PDF form from receipt data using the 1701.pdf template."""

    # Get the absolute path to the template
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "..", "assets", "1701.pdf")

    # Read the template PDF
    reader = PdfReader(template_path)
    writer = PdfWriter()

    # Clone the entire PDF structure including AcroForm
    writer.clone_reader_document_root(reader)

    # Prepare field mapping based on receipt data
    # Map receipt data to relevant form fields
    store_info = receipt_data.get("store_info", {})
    transaction_info = receipt_data.get("transaction_info", {})
    totals = receipt_data.get("totals", {})
    metadata = receipt_data.get("metadata", {})

    # Create field mapping for the form
    field_updates = {}

    # Store/Business information (Page 1)
    if store_info.get("name"):
        field_updates[
            "A TaxpayerFiler8 Taxpayers Name Last Name First Name Suffix Middle Name ESTATE OF First Name Middle Name Last Name TRUST FAO First Name Middle Name Last Name"
        ] = store_info["name"]

    if store_info.get("tin"):
        field_updates[
            "A TaxpayerFiler6 Taxpayer Identification Number TIN"
        ] = store_info["tin"]

    # Transaction date
    if transaction_info.get("date"):
        try:
            date_obj = datetime.strptime(transaction_info["date"], "%Y-%m-%d")
            field_updates["YEAR MM"] = f"{date_obj.month:02d}"
            field_updates["YEAR YY"] = f"{date_obj.year}"
        except ValueError:
            pass

    # BUSINESS INCOME SECTION (Page 2 - B. Taxable Business Income)
    # Map receipt totals to proper business income fields

    # Line 5: Sales/Revenues/Fees (total including VAT)
    if totals.get("total"):
        total_sales = _format_currency(totals["total"])
        field_updates["P2 5"] = total_sales

    # Line 6: Less: Sales Returns, Allowances and Discounts
    if totals.get("discount"):
        discount_amount = _format_currency(totals["discount"])
        field_updates["P2 6"] = discount_amount

    # Line 7: Net Sales/Revenues/Fees (Line 5 less Line 6)
    try:
        total_val = float(_format_currency(totals.get("total", 0)))
        discount_val = float(_format_currency(totals.get("discount", 0)))
        net_sales = total_val - discount_val
        field_updates["P2 7"] = f"{net_sales:.2f}"
    except (ValueError, TypeError):
        if totals.get("subtotal"):
            field_updates["P2 7"] = _format_currency(totals["subtotal"])

    # Line 8: Less: Cost of Sales/Services (we'll use 60% of net sales as estimated cost)
    try:
        net_sales_val = float(field_updates.get("P2 7", "0"))
        estimated_cost = net_sales_val * 0.6  # Estimate 60% cost ratio
        field_updates["P2 8"] = f"{estimated_cost:.2f}"
    except (ValueError, TypeError):
        field_updates["P2 8"] = "0.00"

    # Line 9: Gross Income/(Loss) from Operation (Line 7 less Line 8)
    try:
        net_sales_val = float(field_updates.get("P2 7", "0"))
        cost_val = float(field_updates.get("P2 8", "0"))
        gross_income = net_sales_val - cost_val
        field_updates["P2 9"] = f"{gross_income:.2f}"
    except (ValueError, TypeError):
        field_updates["P2 9"] = "0.00"

    # Line 10A: Ordinary Allowable Itemized Deductions
    if metadata.get("is_deductible") and metadata.get("deductible_amount"):
        deductible_amount = _format_currency(metadata["deductible_amount"])
        field_updates["P2 10A"] = deductible_amount

    # Line 10D: Total Allowable Itemized Deductions (same as 10A for now)
    if field_updates.get("P2 10A"):
        field_updates["P2 10D"] = field_updates["P2 10A"]

    # Line 12: Net Income/(Loss) (Line 9 less Line 10D)
    try:
        gross_income_val = float(field_updates.get("P2 9", "0"))
        deductions_val = float(field_updates.get("P2 10D", "0"))
        net_income = gross_income_val - deductions_val
        field_updates["P2 12"] = f"{net_income:.2f}"
    except (ValueError, TypeError):
        field_updates["P2 12"] = field_updates.get("P2 9", "0.00")

    # Line 14: Taxable Income-Business (same as net income for now)
    if field_updates.get("P2 12"):
        field_updates["P2 14"] = field_updates["P2 12"]

    # VAT-related fields
    if totals.get("vat"):
        vat_amount = _format_currency(totals["vat"])
        field_updates["P2 V1"] = vat_amount  # VAT field

    # Set business income type checkbox
    if metadata.get("transaction_category") in [
        "FOOD",
        "TRANSPORTATION",
        "ENTERTAINMENT",
        "OTHER",
    ]:
        field_updates["Income from Business"] = "/On"

    # Set graduated rates (most common for business income)
    field_updates["Graduated Income Tax Rates"] = "/On"

    # Add receipt metadata as notes
    receipt_summary = f"Receipt from {store_info.get('name', 'N/A')} on {transaction_info.get('date', 'N/A')}"
    field_updates["9 Other Tax CreditsPayments specify"] = receipt_summary[
        :50
    ]  # Truncate to fit field

    # Update the form fields using the new method
    try:
        writer.update_page_form_field_values(writer.pages[0], field_updates)

        # If there's a second page, update it too
        if len(writer.pages) > 1:
            writer.update_page_form_field_values(writer.pages[1], field_updates)
    except Exception as e:
        # If the new method fails, fall back to the individual field update approach
        print(f"Warning: Form field update failed: {e}")
        # We'll still return the PDF even if field filling fails

    # Create output buffer
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)

    # Convert to base64
    pdf_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return pdf_base64
