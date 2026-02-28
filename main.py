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

from processors.image_processor import extract_text_from_image
from processors.pdf_processor import extract_text_from_pdf
from extractor import build_invoice

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
# PROCESS INVOICE
# =========================
def process_invoice(file_path):
    file_hash = get_file_hash(file_path)

    if already_processed(file_hash):
        return None

    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
        text = extract_text_from_image(file_path)

    elif file_path.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_path)

    else:
        raise ValueError("Unsupported file type")

    return build_invoice(text, file_hash)

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