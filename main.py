import os
import time
import shutil
import uuid
import hashlib
import re

import pandas as pd
import pytesseract
from PIL import Image

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ==============================
# CONFIG
# ==============================
INCOMING_DIR = "invoices/incoming"
PROCESSED_DIR = "invoices/processed"
FAILED_DIR = "invoices/failed"
OUTPUT_DIR = "output"

INVOICE_CSV = os.path.join(OUTPUT_DIR, "invoices.csv")
ITEMS_CSV = os.path.join(OUTPUT_DIR, "items.csv")

os.makedirs(INCOMING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# CATEGORY RULES
# ==============================
CATEGORY_RULES = {
    "technology": [
        "computer", "pc", "desktop", "laptop",
        "intel", "nvidia", "workstation"
    ],
    "fashion": [
        "shoes", "shirt", "jeans", "clothing"
    ],
    "home essentials": [
        "mouse", "keyboard", "chair", "table"
    ]
}

# ==============================
# UTILITIES
# ==============================
def get_file_hash(file_path):
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def invoice_already_processed(file_hash):
    if not os.path.exists(INVOICE_CSV):
        return False
    df = pd.read_csv(INVOICE_CSV)
    return file_hash in df["file_hash"].values

# ==============================
# OCR
# ==============================
def extract_text(image_path):
    image = Image.open(image_path)
    return pytesseract.image_to_string(image)

# ==============================
# FIELD EXTRACTION
# ==============================
def extract_vendor(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "Seller" in line:
            return lines[i + 1].strip()
    return "Unknown"

def extract_date(text):
    match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    return match.group() if match else "Unknown"

def extract_total_amount(text):
    for line in text.splitlines():
        if "Total" in line:
            nums = re.findall(r"\d+[.,]\d+", line)
            if nums:
                return float(nums[-1].replace(",", "."))
    return 0.0

# ==============================
# ITEM EXTRACTION
# ==============================
def extract_items(text):
    items = []
    lines = text.splitlines()
    parsing = False

    for line in lines:
        if "ITEMS" in line:
            parsing = True
            continue

        if parsing:
            match = re.match(r"\s*\d+\.\s+(.*)", line)
            if match:
                content = match.group(1)
                prices = re.findall(r"\d+[.,]\d+", content)
                if prices:
                    price = float(prices[-1].replace(",", "."))
                    name = content.replace(prices[-1], "").strip()
                    items.append({
                        "name": name,
                        "price": price
                    })
    return items

# ==============================
# CATEGORIZATION
# ==============================
def categorize_item(name):
    name = name.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in name:
                return category
    return "uncategorized"

# ==============================
# PROCESS SINGLE INVOICE
# ==============================
def process_invoice(file_path):
    text = extract_text(file_path)

    invoice_id = str(uuid.uuid4())
    vendor = extract_vendor(text)
    date = extract_date(text)
    total_amount = extract_total_amount(text)

    invoice_record = {
        "invoice_id": invoice_id,
        "file_hash": get_file_hash(file_path),
        "vendor": vendor,
        "date": date,
        "total_amount": total_amount
    }

    item_records = []
    for item in extract_items(text):
        item_records.append({
            "item_id": str(uuid.uuid4()),
            "invoice_id": invoice_id,
            "item_name": item["name"],
            "price": item["price"],
            "category": categorize_item(item["name"])
        })

    return invoice_record, item_records

# ==============================
# CSV STORAGE
# ==============================
def save_to_csv(invoice, items):
    inv_df = pd.DataFrame([invoice])
    item_df = pd.DataFrame(items)

    if os.path.exists(INVOICE_CSV):
        inv_df.to_csv(INVOICE_CSV, mode="a", index=False, header=False)
    else:
        inv_df.to_csv(INVOICE_CSV, index=False)

    if os.path.exists(ITEMS_CSV):
        item_df.to_csv(ITEMS_CSV, mode="a", index=False, header=False)
    else:
        item_df.to_csv(ITEMS_CSV, index=False)

# ==============================
# AUTOMATION HANDLER
# ==============================
class InvoiceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        time.sleep(1)  # ensure file is fully written

        try:
            file_hash = get_file_hash(file_path)

            if invoice_already_processed(file_hash):
                shutil.move(file_path, PROCESSED_DIR)
                return

            invoice, items = process_invoice(file_path)
            save_to_csv(invoice, items)

            shutil.move(file_path, PROCESSED_DIR)
            print("Processed:", os.path.basename(file_path))

        except Exception as e:
            print("Failed:", e)
            shutil.move(file_path, FAILED_DIR)

# ==============================
# RUN AUTOMATION
# ==============================
if __name__ == "__main__":
    observer = Observer()
    observer.schedule(InvoiceHandler(), INCOMING_DIR, recursive=False)
    observer.start()

    print("Invoice automation running...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()