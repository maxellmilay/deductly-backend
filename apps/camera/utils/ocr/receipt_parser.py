"""
Receipt parsing utilities optimized for Philippine receipts.
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))


class ReceiptParser:
    """Parser for Philippine receipt formats."""

    def __init__(self):
        # Common patterns in Philippine receipts
        self.patterns = {
            "tin": r"(?:TIN|TAX\s+ID|VAT\s+REG\.\s+TIN)[:\s]*(\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3,5})",
            "vat": r"(?:VAT|V\.A\.T\.)[:\s]*(?:Sales|Amount)?[:\s]*([\d,]+\.\d{2})",
            "total": [
                r"(?:TOTAL|GRAND\s+TOTAL|AMOUNT\s+DUE)[:\s]*([\d,]+\.\d{2})",
                r"([\d,]+\.\d{2})\s*(?:TOTAL|GRAND\s+TOTAL)",
                r"([\d,]+\.\d{2})\s*$",  # Amount at end of line
            ],
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
            "item": [
                r"([A-Za-z0-9\s\.]+)\s+([\d,]+\.\d{2})",  # Item name followed by price
                r"([\d,]+\.\d{2})\s+([A-Za-z0-9\s\.]+)",  # Price followed by item name
                r"([A-Za-z0-9\s\.]+)\s+x\s*(\d+)\s+@\s*([\d,]+\.\d{2})",  # Item with quantity and unit price
            ],
            "service_charge": r"(?:Service\s+Charge|SC)[:\s]*([\d,]+\.\d{2})",
            "discount": r"(?:Discount|DISCOUNT)[:\s]*([\d,]+\.\d{2})",
            "payment_method": r"(?:Payment\s+Method|PAYMENT)[:\s]*([A-Za-z0-9\s]+)",
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

    def _process_with_chatgpt(self, text: str) -> Dict[str, Any]:
        """Process extracted text with ChatGPT to get structured data"""
        try:
            prompt = f"""Extract and structure the following receipt information in JSON format. 
            This is a Philippine receipt, so look for:
            - Store name and TIN (Tax Identification Number)
            - Date and time
            - Items with quantities and prices
            - VAT (12%)
            - Service charge
            - Discounts
            - Payment method (Cash, Card, GCash, etc.)
            - Total amount
            
            Format the response as a JSON object with these fields:
            {{
                "store_info": {{
                    "name": "store name",
                    "tin": "TIN number if available",
                    "branch": "branch name if available"
                }},
                "transaction_info": {{
                    "date": "date in YYYY-MM-DD format",
                    "time": "time in HH:MM:SS format",
                    "payment_method": "payment method"
                }},
                "items": [
                    {{
                        "name": "item name",
                        "quantity": "quantity",
                        "price": "price"
                    }}
                ],
                "totals": {{
                    "subtotal": "subtotal",
                    "vat": "VAT amount",
                    "service_charge": "service charge",
                    "discount": "discount amount",
                    "total": "total amount"
                }},
                "metadata": {{
                    "currency": "PHP",
                    "vat_rate": 0.12,
                    "bir_accreditation": "BIR accreditation number if available",
                    "serial_number": "serial number if available"
                }}
            }}

            Receipt text:
            {text}
            """

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts and structures receipt information.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            # Parse the response
            result = response.choices[0].message.content
            try:
                # Try to find JSON in the response
                json_str = re.search(r"\{.*\}", result, re.DOTALL)
                if json_str:
                    return json.loads(json_str.group())
                else:
                    # If no JSON found, return empty structure
                    return self._get_empty_structure()
            except json.JSONDecodeError:
                # If JSON parsing fails, return empty structure
                return self._get_empty_structure()

        except Exception as e:
            print(f"Error processing with ChatGPT: {str(e)}")
            return self._get_empty_structure()

    def _get_empty_structure(self) -> Dict[str, Any]:
        """Return an empty receipt structure."""
        return {
            "store_info": {},
            "transaction_info": {},
            "items": [],
            "totals": {},
            "metadata": {"currency": "PHP", "vat_rate": 0.12},
        }

    def parse_receipt(self, text: str) -> Dict[str, Any]:
        """
        Parse receipt text into structured data.
        Optimized for Philippine receipt formats.
        """
        # Clean text
        text = self._clean_text(text)

        # First try with ChatGPT
        chatgpt_result = self._process_with_chatgpt(text)

        # Then try with regex patterns as fallback
        regex_result = self._parse_with_regex(text)

        # Merge results, preferring ChatGPT's output
        result = self._merge_results(chatgpt_result, regex_result)

        return result

    def _parse_with_regex(self, text: str) -> Dict[str, Any]:
        """Parse receipt using regex patterns as fallback."""
        result = self._get_empty_structure()

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

        # Extract payment method
        payment_match = re.search(self.patterns["payment_method"], text)
        if payment_match:
            result["transaction_info"]["payment_method"] = payment_match.group(
                1
            ).strip()

        # Extract items
        result["items"] = self._extract_items(text)

        # Extract totals
        vat_match = re.search(self.patterns["vat"], text)
        if vat_match:
            result["totals"]["vat"] = float(vat_match.group(1).replace(",", ""))

        service_charge_match = re.search(self.patterns["service_charge"], text)
        if service_charge_match:
            result["totals"]["service_charge"] = float(
                service_charge_match.group(1).replace(",", "")
            )

        discount_match = re.search(self.patterns["discount"], text)
        if discount_match:
            result["totals"]["discount"] = float(
                discount_match.group(1).replace(",", "")
            )

        # Try each total pattern
        for total_pattern in self.patterns["total"]:
            total_match = re.search(total_pattern, text)
            if total_match:
                result["totals"]["total"] = float(total_match.group(1).replace(",", ""))
                break

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

    def _merge_results(
        self, chatgpt_result: Dict[str, Any], regex_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge ChatGPT and regex results, preferring ChatGPT's output."""
        result = chatgpt_result.copy()

        # Fill in any missing fields from regex result
        for key in ["store_info", "transaction_info", "totals", "metadata"]:
            if not result.get(key):
                result[key] = regex_result.get(key, {})
            else:
                for subkey, value in regex_result.get(key, {}).items():
                    if not result[key].get(subkey):
                        result[key][subkey] = value

        # Merge items, preferring ChatGPT's items
        if not result.get("items"):
            result["items"] = regex_result.get("items", [])

        return result

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
                            "name": desc.strip(),
                            "price": float(price.replace(",", "")),
                            "quantity": int(qty),
                        }
                    )
                else:
                    items.append(
                        {
                            "name": description.strip(),
                            "price": float(price.replace(",", "")),
                            "quantity": 1,
                        }
                    )

        return items

    def to_json(self, parsed_data: Dict[str, Any]) -> str:
        """Convert parsed data to JSON string."""
        return json.dumps(parsed_data, indent=2, ensure_ascii=False)

    def to_csv(self, parsed_data: Dict[str, Any]) -> str:
        """Convert parsed data to CSV format."""
        # Implementation for CSV conversion
        pass
