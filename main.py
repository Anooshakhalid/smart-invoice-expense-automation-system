import os
import time
import shutil
import uuid
import hashlib
import json
import re

import pytesseract
from PIL import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# =========================
# CONFIG
# =========================
INCOMING_DIR = "invoices/incoming"
PROCESSED_DIR = "invoices/processed"
FAILED_DIR = "invoices/failed"
OUTPUT_DIR = "output"

DB_PATH = os.path.join(OUTPUT_DIR, "invoices_db.json")

os.makedirs(INCOMING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# CATEGORY RULES
# =========================
CATEGORY_RULES = {
    "technology": ["computer", "pc", "desktop", "laptop", "intel", "nvidia"],
    "fashion": ["shoes", "shirt", "jeans", "clothing"],
    "home essentials": ["mouse", "keyboard", "chair", "table"]
}

# =========================
# JSON DB HELPERS
# =========================
def load_db():
    if not os.path.exists(DB_PATH):
        return {"invoices": []}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)

# =========================
# DEDUPLICATION (HASH)
# =========================
def get_file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def already_processed(file_hash):
    db = load_db()
    for inv in db["invoices"]:
        if inv.get("_hash") == file_hash:
            return True
    return False

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

# def extract_vendor(text):
#     lines = text.splitlines()
#     for i, line in enumerate(lines):
#         if "Seller" in line:
#             return lines[i + 1].strip()
#     return "Unknown"
def extract_vendor(text):
    match = re.search(r"Seller:\s*\n(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else "Unknown"

def extract_date(text):
    match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    return match.group() if match else "Unknown"


def extract_total(text):
    """
    Extract invoice gross worth from SUMMARY section.
    We take the LAST decimal number in the SUMMARY block.
    """
    summary_match = re.search(r"SUMMARY(.*)", text, re.DOTALL | re.IGNORECASE)
    if not summary_match:
        return 0.0

    summary_text = summary_match.group(1)

    numbers = re.findall(r"\d+[.,]\d+", summary_text)

    if numbers:
        return float(numbers[-1].replace(",", "."))  # last number = gross total

    return 0.0

# =========================
# ITEM EXTRACTION
# =========================
def extract_items(text):
    items = []

    # Extract section between ITEMS and SUMMARY
    match = re.search(r"ITEMS(.*?)SUMMARY", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return items

    block = match.group(1)

    # Normalize whitespace (important for OCR)
    block = re.sub(r"\s+", " ", block)

    # Split using item numbers like "1." "2." etc.
    raw_items = re.split(r"\b\d+\.\s*", block)

    for raw in raw_items:
        raw = raw.strip()
        if not raw:
            continue

        # Extract all decimal numbers
        numbers = re.findall(r"\d+[.,]\d+", raw)

        if not numbers:
            continue

        # Last number = Gross worth
        price = float(numbers[-1].replace(",", "."))

        # Remove all numeric values and VAT percentages
        cleaned = re.sub(r"\d+[.,]?\d*", "", raw)
        cleaned = re.sub(r"\d+%", "", cleaned)
        cleaned = cleaned.replace("each", "")
        cleaned = cleaned.strip()

        # Remove leftover double spaces
        cleaned = re.sub(r"\s{2,}", " ", cleaned)

        items.append({
            "name": cleaned,
            "price": price
        })

    return items
# def extract_items(text):
#     items = []

#     # Extract ITEMS → SUMMARY block
#     match = re.search(r"ITEMS(.*?)SUMMARY", text, re.DOTALL | re.IGNORECASE)
#     if not match:
#         return items

#     block = match.group(1)

#     # Normalize spacing but KEEP item numbers
#     block = re.sub(r"\r", "", block)

#     # Split using lookahead so numbers stay grouped correctly
#     raw_items = re.split(r"(?=\n?\s*\d+\.\s*)", block)

#     for raw in raw_items:
#         raw = raw.strip()

#         # Skip headers
#         if not raw or raw.lower().startswith("no"):
#             continue

#         # Extract all decimal numbers
#         numbers = re.findall(r"\d+,\d+", raw)

#         if not numbers:
#             continue

#         # LAST number = Gross worth
#         gross_price = float(numbers[3].replace(",", "."))

#         # Remove numeric-only lines & VAT
#         lines = raw.splitlines()
#         desc_parts = []

#         for line in lines:
#             line = line.strip()

#             # Skip pure numbers (qty, net, etc.)
#             if re.fullmatch(r"\d+,\d+", line):
#                 continue
#             if "%" in line:
#                 continue
#             if line.lower() == "each":
#                 continue
#             if re.match(r"\d+\.", line):
#                 continue

#             desc_parts.append(line)

#         name = " ".join(desc_parts)
#         name = re.sub(r"\s{2,}", " ", name).strip()

#         items.append({
#             "name": name,
#             "price": gross_price
#         })

#     return items

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

# =========================
# PROCESS INVOICE
# =========================
def process_invoice(file_path):
    text = extract_text(file_path)
    file_hash = get_file_hash(file_path)

    if already_processed(file_hash):
        return None  # skip duplicate

    invoice = {
        "invoice_id": str(uuid.uuid4()),
        "invoice_no": extract_invoice_no(text),
        "vendor": extract_vendor(text),
        "date": extract_date(text),
        "total_amount": extract_total(text),
        "items": [],
        "_hash": file_hash  # internal only
    }

    for item in extract_items(text):
        invoice["items"].append({
            "item_id": str(uuid.uuid4()),
            "name": item["name"],
            "price": item["price"],
            "category": categorize(item["name"])
        })

    return invoice

# =========================
# SAVE TO DB
# =========================
def save_invoice(invoice):
    db = load_db()
    db["invoices"].append(invoice)
    save_db(db)

# =========================
# FILE HANDLER
# =========================
class InvoiceHandler(FileSystemEventHandler):
    def handle_file(self, path):
        try:
            invoice = process_invoice(path)

            if invoice:
                save_invoice(invoice)

            shutil.move(path, PROCESSED_DIR)
            print("Processed:", os.path.basename(path))

        except Exception as e:
            print("Failed:", e)
            shutil.move(path, FAILED_DIR)

    def on_created(self, event):
        if not event.is_directory:
            time.sleep(1)
            self.handle_file(event.src_path)

# =========================
# INITIAL PROCESSING
# =========================
def process_existing_files(handler):
    for file in os.listdir(INCOMING_DIR):
        path = os.path.join(INCOMING_DIR, file)
        if os.path.isfile(path):
            handler.handle_file(path)

# =========================
# RUN AUTOMATION
# =========================
if __name__ == "__main__":
    handler = InvoiceHandler()

    # Process already-existing invoices
    process_existing_files(handler)

    # Watch for new ones
    observer = Observer()
    observer.schedule(handler, INCOMING_DIR, recursive=False)
    observer.start()

    print("Invoice automation running...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()