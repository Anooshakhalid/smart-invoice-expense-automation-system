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
    # Capture text between "Seller:" and "Tax Id"
    match = re.search(
        r"Seller:.*?\n(.*?)\n\s*Tax Id",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if not match:
        return "Unknown"

    block = match.group(1)

    # Clean block
    lines = [line.strip() for line in block.splitlines() if line.strip()]

    # First clean line = vendor name
    return lines[0] if lines else "Unknown"
def extract_date(text):
    match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    return match.group() if match else "Unknown"



def extract_total(text):
    """
    Extract invoice gross worth from SUMMARY section.
    We take the LAST decimal number in the SUMMARY block.
    Extract final Gross worth total.
    Handles:
    - 2 012,51
    - $ 2 012,51
    - 228,68
    """
    matches = re.findall(
        r"Gross\s*worth\s*\n?\$?\s*([\d\s]+,\d{2})",
        text,
        re.IGNORECASE
    )

    if matches:
        total_str = matches[-1]
        total_str = total_str.replace(" ", "")
        return float(total_str.replace(",", "."))

    # Fallback for single-item layout
    inline_match = re.search(
        r"\d+,\d{2}\s+each\s+\d+,\d{2}\s+\d+,\d{2}\s+\d+%\s+(\d+,\d{2})",
        text,
        re.IGNORECASE
    )

    if inline_match:
        return float(inline_match.group(1).replace(",", "."))

    return 0.0
    

# =========================
# ITEM EXTRACTION
# =========================

def extract_items(text):
    items = []

    #  Extract ITEMS block
    items_match = re.search(r"ITEMS(.*?)SUMMARY", text, re.DOTALL | re.IGNORECASE)
    if not items_match:
        return items

    block = items_match.group(1)

    # Remove header line
    block = re.sub(r"No\.\s*Description\s*Qty", "", block, flags=re.IGNORECASE)

    # Normalize spacing
    block = re.sub(r"\r", "", block)

    # Split using quantity pattern (e.g. 2,00 3,00 1,00)
    raw_items = re.split(r"\n(?=.*\d+,\d{2})", block)

    descriptions = []

    for raw in raw_items:
        raw = raw.strip()
        if not raw:
            continue

        # Must contain quantity
        qty_match = re.search(r"\d+,\d{2}", raw)
        if not qty_match:
            continue

        # Remove quantity
        raw = re.sub(r"\d+,\d{2}", "", raw)

        # Remove item numbers like "1."
        raw = re.sub(r"^\d+\.\s*", "", raw)

        # Clean whitespace
        raw = re.sub(r"\s+", " ", raw).strip()

        descriptions.append(raw)

    # Extract gross worth list from SUMMARY
    summary_match = re.search(r"Gross\s*worth(.*?)(?:Gross worth|\$)", text, re.DOTALL | re.IGNORECASE)
    if not summary_match:
        return []

    summary_block = summary_match.group(1)

    gross_values = re.findall(r"\d+,\d{2}", summary_block)

    gross_prices = [float(v.replace(",", ".")) for v in gross_values]

    #  Match descriptions with gross prices by order
    for i in range(min(len(descriptions), len(gross_prices))):
        items.append({
            "name": descriptions[i],
            "price": gross_prices[i]
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

    print("\n" + "="*60)
    print("Extracted OCR Text from:", os.path.basename(file_path))
    print("="*60)
    print(text)
    print("="*60 + "\n")

    file_hash = get_file_hash(file_path)

    if already_processed(file_hash):
        print("Duplicate invoice detected. Skipping.")
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