import os
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ocr_extraction import process_invoice
from utils import save_db, load_db
from pdf_extraction import process_pdf_invoice
from email_service import send_invoice_email

INCOMING_DIR = "invoices/incoming"
PROCESSED_DIR = "invoices/processed"
FAILED_DIR = "invoices/failed"

os.makedirs(INCOMING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

# FILE HANDLER
class InvoiceHandler(FileSystemEventHandler):
    def handle_file(self, path):
        try:
            if path.lower().endswith(".pdf"):
                invoice = process_pdf_invoice(path)
            else:
                invoice = process_invoice(path)
            if invoice:
                db = load_db()
                db["invoices"].append(invoice)
                save_db(db)

                # Send email notification
                send_invoice_email(invoice)

            shutil.move(path, PROCESSED_DIR)
            print("Processed:", os.path.basename(path))
        except Exception as e:
            print("Failed:", e)
            shutil.move(path, FAILED_DIR)

    def on_created(self, event):
        if not event.is_directory:
            time.sleep(1)
            self.handle_file(event.src_path)

# INITIAL PROCESSING
def process_existing_files(handler):
    for file in os.listdir(INCOMING_DIR):
        path = os.path.join(INCOMING_DIR, file)
        if os.path.isfile(path):
            handler.handle_file(path)

# MAIN
if __name__ == "__main__":
    handler = InvoiceHandler()
    process_existing_files(handler)

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