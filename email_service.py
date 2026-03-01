import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# =========================
# CONFIGURATION
# =========================
SMTP_SERVER = "smtp.gmail.com"  # Change if not Gmail
SMTP_PORT = 587

SENDER_EMAIL = "zia4500438@cloud.neduet.edu.pk"
SENDER_PASSWORD = ""  # ⚠️ Replace

RECIPIENTS = [
    "laibaiqrarahmedkhan@gmail.com",
    "anooshakhalid999@gmail.com"
]


# =========================
# SEND EMAIL FUNCTION
# =========================
def send_invoice_email(invoice):

    subject = f"New Invoice Processed - {invoice['invoice_no']}"

    body = f"""
Invoice Summary

Invoice No: {invoice['invoice_no']}
Vendor: {invoice['vendor']}
Date: {invoice['date']}
Total Amount: ${invoice['total_amount']:,.2f}

Items:
"""

    for item in invoice["items"]:
        body += f"- {item['name']} | ${item['price']:,.2f} | {item['category']}\n"

    # Create message
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECIPIENTS)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())
        server.quit()

        print("Email notification sent successfully.")

    except Exception as e:
        print("Failed to send email:", e)