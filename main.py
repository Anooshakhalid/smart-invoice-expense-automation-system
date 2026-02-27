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

def extract_vendor(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "Seller" in line:
            return lines[i + 1].strip()
    return "Unknown"

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

    # Extract everything between ITEMS and SUMMARY
    items_block = re.search(r"ITEMS(.*?)SUMMARY", text, re.DOTALL | re.IGNORECASE)
    if not items_block:
        return items

    block = items_block.group(1)

    # Split by item numbers (1. 2. 3. etc.)
    raw_items = re.split(r"\n\s*\d+\.\s*\n", block)

    for raw in raw_items:
        raw = raw.strip()
        if not raw:
            continue

        lines = [l.strip() for l in raw.splitlines() if l.strip()]

        numbers = re.findall(r"\d+[.,]\d+", raw)

        if not numbers:
            continue

        # Last number in block = Gross worth
        price = float(numbers[-1].replace(",", "."))

        # Remove numeric-only lines and % lines from description
        desc_lines = []
        for l in lines:
            if re.fullmatch(r"\d+[.,]?\d*", l):
                continue
            if "%" in l:
                continue
            if l.lower() == "each":
                continue
            desc_lines.append(l)

        name = " ".join(desc_lines)

        items.append({
            "name": name.strip(),
            "price": price
        })

    return items
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