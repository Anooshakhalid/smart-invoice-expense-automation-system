import re
import uuid
from PIL import Image
import pytesseract
from utils import get_file_hash, already_processed, categorize

# =========================
# OCR
# =========================
def extract_text(image_path):
    return pytesseract.image_to_string(Image.open(image_path))

# =========================
# FIELD EXTRACTION
# =========================
def extract_invoice_no(text):
    match = re.search(r"Invoice\s*no[:\-]?\s*(\d+)", text, re.IGNORECASE)
    return match.group(1) if match else "Unknown"

def extract_vendor(text):
    match = re.search(r"Seller:.*?\n(.*?)\n\s*Tax Id", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return "Unknown"
    lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    return lines[0] if lines else "Unknown"

def extract_date(text):
    match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    return match.group() if match else "Unknown"

def extract_total(text):
    matches = re.findall(r"Gross\s*worth\s*\n?\$?\s*([\d\s]+,\d{2})", text, re.IGNORECASE)
    if matches:
        total_str = matches[-1].replace(" ", "")
        return float(total_str.replace(",", "."))
    # Fallback
    inline_match = re.search(r"\d+,\d{2}\s+each\s+\d+,\d{2}\s+\d+,\d{2}\s+\d+%\s+(\d+,\d{2})", text, re.IGNORECASE)
    if inline_match:
        return float(inline_match.group(1).replace(",", "."))
    return 0.0

# =========================
# ITEM EXTRACTION
# =========================
def extract_items(text):
    items = []
    items_match = re.search(r"ITEMS(.*?)SUMMARY", text, re.DOTALL | re.IGNORECASE)
    if not items_match:
        return items
    block = items_match.group(1)
    block = re.sub(r"No\.\s*Description\s*Qty", "", block, flags=re.IGNORECASE)
    block = re.sub(r"\r", "", block)
    raw_items = re.split(r"\n(?=.*\d+,\d{2})", block)
    descriptions = []

    for raw in raw_items:
        raw = raw.strip()
        if not raw:
            continue
        qty_match = re.search(r"\d+,\d{2}", raw)
        if not qty_match:
            continue
        raw = re.sub(r"\d+,\d{2}", "", raw)
        raw = re.sub(r"^\d+\.\s*", "", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        descriptions.append(raw)

    summary_match = re.search(r"Gross\s*worth(.*?)(?:Gross worth|\$)", text, re.DOTALL | re.IGNORECASE)
    if not summary_match:
        return []

    gross_values = re.findall(r"\d+,\d{2}", summary_match.group(1))
    gross_prices = [float(v.replace(",", ".")) for v in gross_values]

    for i in range(min(len(descriptions), len(gross_prices))):
        items.append({
            "name": descriptions[i],
            "price": gross_prices[i],
            "category": categorize(descriptions[i])
        })

    return items

# =========================
# PROCESS INVOICE
# =========================
def process_invoice(file_path):
    text = extract_text(file_path)
    print("\n" + "="*60)
    print("Extracted OCR Text from:", file_path)
    print("="*60)
    print(text)
    print("="*60 + "\n")

    file_hash = get_file_hash(file_path)
    if already_processed(file_hash):
        print("Duplicate invoice detected. Skipping.")
        return None

    invoice = {
        "invoice_id": str(uuid.uuid4()),
        "invoice_no": extract_invoice_no(text),
        "vendor": extract_vendor(text),
        "date": extract_date(text),
        "total_amount": extract_total(text),
        "items": extract_items(text),
        "_hash": file_hash
    }

    return invoice