import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import base64


def _format_currency(value):
    """Safely format currency values."""
    try:
        # Remove any commas and convert to float
        if isinstance(value, str):
            value = value.replace(",", "")
        return f"P{float(value):.2f}"
    except (ValueError, TypeError):
        return "P0.00"


def generate_receipt_pdf(receipt_data):
    """Generate a PDF from receipt data."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Add title
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=30
    )
    elements.append(
        Paragraph(
            f"Receipt from {receipt_data.get('store_info', {}).get('name', 'Unknown Vendor')}",
            title_style,
        )
    )
    elements.append(Spacer(1, 20))

    # Add store information
    store_info = receipt_data.get("store_info", {})
    store_data = [
        ["Store Name:", store_info.get("name", "N/A")],
        ["Address:", store_info.get("address", "N/A")],
        ["Contact:", store_info.get("contact_number", "N/A")],
        ["Email:", store_info.get("email", "N/A")],
    ]
    store_table = Table(store_data, colWidths=[2 * inch, 4 * inch])
    store_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.grey),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(store_table)
    elements.append(Spacer(1, 20))

    # Add items
    items = receipt_data.get("items", [])
    if items:
        # Create table data
        table_data = [["Item", "Quantity", "Price", "Subtotal"]]
        for item in items:
            table_data.append(
                [
                    item.get("title", "N/A"),
                    str(item.get("quantity", 0)),
                    _format_currency(item.get("price", 0)),
                    _format_currency(item.get("subtotal", 0)),
                ]
            )

        # Create table
        items_table = Table(
            table_data, colWidths=[3 * inch, 1 * inch, 1 * inch, 1 * inch]
        )
        items_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        elements.append(items_table)
        elements.append(Spacer(1, 20))

    # Add totals
    totals = receipt_data.get("totals", {})
    totals_data = [
        ["Subtotal:", _format_currency(totals.get("total_expediture", 0))],
        ["Discount:", _format_currency(totals.get("discount", 0))],
        ["VAT:", _format_currency(totals.get("value_added_tax", 0))],
        ["Total:", _format_currency(totals.get("total_expediture", 0))],
    ]
    totals_table = Table(totals_data, colWidths=[2 * inch, 2 * inch])
    totals_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(totals_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    # Convert to base64
    pdf_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return pdf_base64
