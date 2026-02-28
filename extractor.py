import re
import uuid

# =========================
# FIELD EXTRACTION
# =========================
def extract_invoice_no(text):
    match = re.search(r"#\s*(\d+)", text)
    if match:
        return match.group(1)

    match = re.search(r"Invoice\s*no[:\-]?\s*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)

    return "Unknown"

def extract_vendor(text):
    lines = text.splitlines()

    # PDF format (SuperStore)
    for i, line in enumerate(lines):
        if "INVOICE" in line.upper() and i + 2 < len(lines):
            return lines[i + 2].strip()

    # Image format (Seller:)
    match = re.search(r"Seller:\s*\n(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return "Unknown"

def extract_date(text):
    match = re.search(r"[A-Za-z]{3}\s\d{1,2}\s\d{4}", text)
    if match:
        return match.group()

    match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    if match:
        return match.group()

    return "Unknown"


def extract_total(text):
    match = re.search(r"Total:\s*\$?([\d,]+\.\d+)", text)
    if match:
        return float(match.group(1).replace(",", ""))

    match = re.search(r"Balance Due:\s*\$?([\d,]+\.\d+)", text)
    if match:
        return float(match.group(1).replace(",", ""))

    return 0.0

# =========================
# ITEM EXTRACTION
# =========================
def extract_items_from_ocr(text):
    items = []

    # Find ITEMS section start
    items_start = re.search(r"ITEMS", text, re.IGNORECASE)
    summary_start = re.search(r"SUMMARY", text, re.IGNORECASE)

    if not items_start or not summary_start:
        return items

    block = text[items_start.end():summary_start.start()]

    # Normalize whitespace
    block = re.sub(r"\s+", " ", block)

    # Split by item number pattern (1. 2. 3.)
    raw_items = re.split(r"\s\d+\.\s", block)

    for raw in raw_items:
        raw = raw.strip()
        if not raw:
            continue

        numbers = re.findall(r"\d+[.,]\d+", raw)
        if len(numbers) < 1:
            continue

        # LAST decimal number = gross price
        price = float(numbers[-1].replace(",", "."))

        # Remove numbers and VAT
        cleaned = re.sub(r"\d+[.,]?\d*", "", raw)
        cleaned = re.sub(r"\d+%", "", cleaned)
        cleaned = cleaned.replace("each", "")
        cleaned = cleaned.strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)

        items.append({
            "name": cleaned,
            "price": price
        })

    return items

def extract_items(text):
    # Try structured PDF format first
    pattern = r"(.+?)\s+(\d+)\s+\$([\d,]+\.\d+)\s+\$([\d,]+\.\d+)"
    matches = re.findall(pattern, text)

    if matches:
        items = []
        for match in matches:
            name = match[0].strip()
            amount = float(match[3].replace(",", ""))

            items.append({
                "name": name,
                "price": amount
            })
        return items

    # Otherwise fallback to OCR logic
    return extract_items_from_ocr(text)

# =========================
# CATEGORY RULES
# =========================
CATEGORY_RULES = {
    "technology": ["computer", "pc", "desktop", "laptop", "intel", "nvidia"],
    "fashion": ["shoes", "shirt", "jeans", "clothing"],
    "home essentials": ["mouse", "keyboard", "chair", "table"]
}


# =========================
# CATEGORIZATION
# =========================
def categorize(name):
    name = name.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in name:
                return category
    return "uncategorized"

def build_invoice(text, file_hash):
    return {
        "invoice_id": str(uuid.uuid4()),
        "invoice_no": extract_invoice_no(text),
        "vendor": extract_vendor(text),
        "date": extract_date(text),
        "total_amount": extract_total(text),
        "items": [
            {
                "item_id": str(uuid.uuid4()),
                "name": item["name"],
                "price": item["price"],
                "category": categorize(item["name"])
            }
            for item in extract_items(text)
        ],
        "_hash": file_hash
    }