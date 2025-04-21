"""
Receipt parsing utilities optimized for Philippine receipts.
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import json


class ReceiptParser:
    """Parser for Philippine receipt formats."""

    def __init__(self):
        # Common patterns in Philippine receipts
        self.patterns = {
            "tin": r"(?:TIN|TAX\s+ID|VAT\s+REG\.\s+TIN)[:\s]*(\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3,5})",
            "vat": r"(?:VAT|V\.A\.T\.)[:\s]*(?:Sales|Amount)?[:\s]*([\d,]+\.\d{2})",
            "total": r"(?:TOTAL|GRAND\s+TOTAL|AMOUNT\s+DUE)[:\s]*([\d,]+\.\d{2})",
            "date": [
                r"(\d{2}/\d{2}/\d{2,4})",
                r"(\d{2}-\d{2}-\d{2,4})",
                r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})",
            ],
            "time": r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)",
            "store_name": r"^([A-Z][A-Za-z0-9\s&\.,]+)(?:\n|$)",
            "branch": r"(?:Branch|BRANCH)[:\s]*([A-Za-z0-9\s\.,]+)(?:\n|$)",
            "bir_accred": r"(?:BIR\s+Accred(?:itation)?|PTU\s+No\.)[:\s]*([A-Za-z0-9\-]+)",
            "serial_no": r"(?:Serial\s+No|Machine\s+No)[:\s]*([A-Za-z0-9\-]+)",
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Replace common OCR mistakes
        replacements = {
            "O": "0",
            "l": "1",
            "I": "1",
            "S": "5",
            "B": "8",
        }

        # Clean text
        text = text.strip()
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if line:  # Skip empty lines
                # Fix common OCR mistakes in numbers
                for char, replacement in replacements.items():
                    # Only replace if it's in a number context
                    line = re.sub(rf"(?<=\d){char}(?=\d)", replacement, line)
                    line = re.sub(rf"(?<=\d){char}$", replacement, line)
                    line = re.sub(rf"^{char}(?=\d)", replacement, line)
                lines.append(line)

        return "\n".join(lines)

    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract items and prices from receipt text."""
        items = []
        current_section = None

        # Common section headers in Philippine receipts
        section_headers = {
            "items": r"^(?:ITEMS|PURCHASED\s+ITEMS|SALE)",
            "subtotal": r"^(?:SUBTOTAL|SUB\s*TOTAL)",
            "tax": r"^(?:VAT|TAX)",
            "total": r"^(?:TOTAL|GRAND\s+TOTAL)",
        }

        # Item pattern with optional quantity
        item_pattern = (
            r"^((?:\d+\s*[@xX]\s*)?[A-Za-z0-9\s\-\&\.\,]+)\s+([\d,]+\.\d{2})$"
        )

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a section header
            is_header = False
            for section, pattern in section_headers.items():
                if re.match(pattern, line, re.IGNORECASE):
                    current_section = section
                    is_header = True
                    break

            if is_header:
                continue

            # Try to match item pattern
            match = re.match(item_pattern, line)
            if match and current_section != "total":
                description, price = match.groups()

                # Extract quantity if present
                qty_match = re.match(r"^(\d+)\s*[@xX]\s*(.+)$", description)
                if qty_match:
                    qty, desc = qty_match.groups()
                    items.append(
                        {
                            "description": desc.strip(),
                            "price": float(price.replace(",", "")),
                            "quantity": int(qty),
                        }
                    )
                else:
                    items.append(
                        {
                            "description": description.strip(),
                            "price": float(price.replace(",", "")),
                            "quantity": 1,
                        }
                    )

        return items

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string into ISO format."""
        date_formats = [
            "%d/%m/%y",
            "%d/%m/%Y",
            "%m/%d/%y",
            "%m/%d/%Y",
            "%d-%m-%y",
            "%d-%m-%Y",
            "%d %b %Y",
            "%d %B %Y",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def _parse_time(self, time_str: str) -> Optional[str]:
        """Parse time string into 24-hour format."""
        time_formats = [
            "%H:%M",
            "%H:%M:%S",
            "%I:%M %p",
            "%I:%M:%S %p",
        ]

        for fmt in time_formats:
            try:
                return datetime.strptime(time_str, fmt).strftime("%H:%M:%S")
            except ValueError:
                continue
        return None

    def parse_receipt(self, text: str) -> Dict[str, Any]:
        """
        Parse receipt text into structured data.
        Optimized for Philippine receipt formats.
        """
        # Clean text
        text = self._clean_text(text)

        # Initialize result dictionary
        result = {
            "store_info": {},
            "transaction_info": {},
            "items": [],
            "totals": {},
            "metadata": {},
        }

        # Extract store information
        store_match = re.search(self.patterns["store_name"], text, re.MULTILINE)
        if store_match:
            result["store_info"]["name"] = store_match.group(1).strip()

        branch_match = re.search(self.patterns["branch"], text, re.MULTILINE)
        if branch_match:
            result["store_info"]["branch"] = branch_match.group(1).strip()

        tin_match = re.search(self.patterns["tin"], text)
        if tin_match:
            result["store_info"]["tin"] = (
                tin_match.group(1).replace(" ", "").replace("-", "")
            )

        # Extract transaction date and time
        for date_pattern in self.patterns["date"]:
            date_match = re.search(date_pattern, text)
            if date_match:
                parsed_date = self._parse_date(date_match.group(1))
                if parsed_date:
                    result["transaction_info"]["date"] = parsed_date
                break

        time_match = re.search(self.patterns["time"], text)
        if time_match:
            parsed_time = self._parse_time(time_match.group(1))
            if parsed_time:
                result["transaction_info"]["time"] = parsed_time

        # Extract items
        result["items"] = self._extract_items(text)

        # Extract totals
        vat_match = re.search(self.patterns["vat"], text)
        if vat_match:
            result["totals"]["vat"] = float(vat_match.group(1).replace(",", ""))

        total_match = re.search(self.patterns["total"], text)
        if total_match:
            result["totals"]["total"] = float(total_match.group(1).replace(",", ""))

        # Calculate subtotal if not explicitly found
        if result["totals"].get("total") and result["totals"].get("vat"):
            result["totals"]["subtotal"] = (
                result["totals"]["total"] - result["totals"]["vat"]
            )

        # Extract metadata
        bir_match = re.search(self.patterns["bir_accred"], text)
        if bir_match:
            result["metadata"]["bir_accreditation"] = bir_match.group(1)

        serial_match = re.search(self.patterns["serial_no"], text)
        if serial_match:
            result["metadata"]["serial_number"] = serial_match.group(1)

        return result

    def to_json(self, parsed_data: Dict[str, Any]) -> str:
        """Convert parsed data to JSON string."""
        return json.dumps(parsed_data, indent=2, ensure_ascii=False)

    def to_csv(self, parsed_data: Dict[str, Any]) -> str:
        """Convert parsed data to CSV format."""
        csv_lines = []

        # Header
        csv_lines.append("Item,Quantity,Price")

        # Items
        for item in parsed_data.get("items", []):
            csv_lines.append(
                f"{item['description']},{item.get('quantity', 1)},{item['price']}"
            )

        # Totals
        totals = parsed_data.get("totals", {})
        if totals:
            csv_lines.extend(
                [
                    "",
                    f"Subtotal,{totals.get('subtotal', '')}",
                    f"VAT,{totals.get('vat', '')}",
                    f"Total,{totals.get('total', '')}",
                ]
            )

        return "\n".join(csv_lines)
