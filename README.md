# 📄 Smart Invoice & Expense Automation System

An end-to-end automated invoice processing and expense reporting system that extracts invoice data (PDF & Image), categorizes expenses, stores structured records, sends email notifications, and generates real-time financial analytics via an interactive dashboard.

---

## 🚀 One-Line Pitch

An intelligent automation workflow that extracts invoice data, categorizes expenses, stores them in a structured database, sends email alerts, and provides real-time financial insights.

---

## 📌 Project Overview

The Smart Invoice & Expense Automation System is built for:

- Small businesses  
- Startups  
- Freelancers  
- Finance teams  
- Accounting departments  

It eliminates manual invoice processing by automating:

- Invoice data extraction
- Expense categorization
- Data storage
- Report generation
- Email notifications
- Real-time dashboard analytics

---

## ✨ Key Features

### 1️⃣ Invoice Upload (PDF & Image Support)

- Monitors `invoices/incoming/` directory
- Automatically detects file type:
  - 🖼 Image → OCR Extraction
  - 📄 PDF → Text Extraction
- Processes invoices in real time

---

### 2️⃣ Intelligent Field Extraction

Automatically extracts:

- Invoice Number
- Vendor Name
- Invoice Date
- Total Amount
- Item Names
- Item Prices

Uses:

- Regex-based pattern matching
- Multi-format PDF detection
- Tesseract OCR for image invoices

---

### 3️⃣ Rule-Based Expense Categorization

Each invoice item is categorized using keyword rules.

Categories include:

- Technology
- Fashion
- Home Essentials
- Uncategorized

Implemented inside `utils.py`.

---

### 4️⃣ Duplicate Invoice Detection

- Generates MD5 hash for each file
- Prevents duplicate entries
- Ensures database integrity

---

### 5️⃣ Structured JSON Database

All invoices are stored in:
output/invoices_db.json

## 6️⃣ Automatic Email Notifications

When a new invoice is processed:

- 📧 Email summary is automatically sent  
- Contains invoice details and item breakdown  
- Supports multiple recipients  
- Uses secure SMTP authentication  

---

## 7️⃣ Real-Time Analytics Dashboard (Streamlit)

Interactive dashboard includes:

- 💰 Total Revenue  
- 📄 Total Invoices  
- 📊 Top Vendors  
- 📈 Revenue by Category  
- 🏢 Revenue by Vendor  
- 📅 Yearly Invoice Trends  
- 📆 Monthly Revenue Trends  
- 🔝 Top 5 Expensive Invoices  

---

## 🔄 How It Works

### Step 1: Drop Invoice

Upload invoice that goes in invoices/incoming/


---

### Step 2: Automatic Processing

`main.py` detects new file using Watchdog.

---

### Step 3: Extraction

- Images → OCR via Tesseract  
- PDFs → Parsed via pdfplumber  

---

### Step 4: Data Structuring

Invoice converted to standardized JSON format.

---

### Step 5: Save to Database

Appends invoice to `invoices_db.json`.

---

### Step 6: Email Notification

Sends invoice summary email automatically.

---

### Step 7: Dashboard Update

Dashboard auto-refreshes and reflects updated data.

---

## 📁 Project Structure
smart-invoice-expense-automation-system/
│
├── invoices/
│ ├── incoming/
│ ├── processed/
│ └── failed/
│
├── output/
│ └── invoices_db.json
│
├── reporting/
│ ├── dashboard.py
│ ├── report_service.py
│ └── init.py
│
├── main.py
├── ocr_extraction.py
├── pdf_extraction.py
├── email_service.py
├── utils.py
├── requirements.txt
└── README.md

## ⚠️ Challenges Faced

During the development of this Smart Invoice & Expense Automation System, several real-world technical challenges were encountered and resolved:

---

### 1️⃣ Inconsistent PDF Text Extraction

- PDF layouts vary significantly across vendors.
- `pdfplumber` sometimes merges columns or rearranges text.
- Fields like **Invoice No** and **Vendor** appeared on the same line unexpectedly.
- Required robust regex patterns and multi-format parsing logic.

✅ Solution:  
Implemented format detection logic and adaptive regex-based extraction.

---

### 2️⃣ Multi-Format Invoice Handling

- Different invoice templates had completely different structures.
- Some PDFs placed labels and values on separate lines.
- OCR-based images had noisy or inconsistent text.

✅ Solution:  
Created separate parsers (`parse_format_1`, `parse_format_2`) with intelligent format detection.

---

### 3️⃣ OCR Noise & Text Imperfections

- Image invoices extracted via Tesseract sometimes contained:
  - Extra spaces
  - Broken words
  - Misaligned fields

✅ Solution:  
Applied pattern matching with fallback logic and keyword-based detection to improve reliability.

---

### 4️⃣ Email Authentication Issues

- Gmail blocks normal password authentication.
- Encountered SMTP authentication errors (Error 535).

✅ Solution:  
Configured Gmail App Passwords and implemented secure environment-variable-based credential handling.

---

### 5️⃣ Import Path & Package Structure Issues

- Streamlit execution caused module import errors.
- Running dashboard from subdirectories broke relative imports.

✅ Solution:  
Restructured project into a proper package layout and corrected module import paths.

---

### 6️⃣ File Overwrite & Duplicate Handling

- Moving processed invoices caused overwrite errors.
- Same invoice uploaded multiple times created duplicate records.

✅ Solution:  
Implemented:
- Safe file renaming during move operations
- MD5 hash-based deduplication system

---

## ⚙ Installation & Setup

### 1️⃣ Clone Repository
```bash
git clone <your-repo-url>
cd smart-invoice-expense-automation-system

###2️⃣ Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

###3️⃣ Install Dependencies
pip install -r requirements.txt

###4️⃣ Install Tesseract (For OCR Support)
sudo apt install tesseract-ocr

▶ Running the System
Terminal 1 — Start Automation Engine
python main.py
Terminal 2 — Start Dashboard
streamlit run reporting/dashboard.py

Open browser:
http://localhost:8501
