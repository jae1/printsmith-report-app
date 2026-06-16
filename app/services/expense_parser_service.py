import imaplib
import email
from email.header import decode_header
import re
import json
import os
import io
from datetime import datetime
from pypdf import PdfReader
from app.core.config import SMTP_CONFIG
from app.services import spending_service

PROCESSED_EMAILS_FILE = "processed_receipts.json"

def _load_processed_ids():
    if not os.path.exists(PROCESSED_EMAILS_FILE):
        return set()
    try:
        with open(PROCESSED_EMAILS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def _save_processed_id(msg_id):
    if not msg_id: return
    ids = _load_processed_ids()
    ids.add(str(msg_id))
    with open(PROCESSED_EMAILS_FILE, "w") as f:
        json.dump(list(ids), f)

def remove_processed_id(msg_id):
    if not msg_id: return
    msg_id_str = str(msg_id)
    ids = _load_processed_ids()
    if msg_id_str in ids:
        print(f"DEBUG: Removing {msg_id_str} from processed history to allow re-sync.")
        ids.discard(msg_id_str)
        with open(PROCESSED_EMAILS_FILE, "w") as f:
            json.dump(list(ids), f)
    else:
        print(f"DEBUG: {msg_id_str} not found in processed history.")

def clean_html(html_content):
    # Basic HTML strip
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # Clean up whitespace
    return " ".join(text.split())

def extract_amount(text):
    if not text:
        return None
    # Look for common patterns including invoice-specific ones
    patterns = [
        r"(?:Order Total|Total|Grand Total|Amount Paid|TOTAL DUE|Invoice Total)[:\s]*\$?\s*([\d,]+\.\d{2})",
        r"Total\s*Amount\s*[:\s]*\$?\s*([\d,]+\.\d{2})",
        r"\$\s*([\d,]+\.\d{2})"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
    return None

def extract_text_from_pdf(pdf_bytes):
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return ""

def fetch_and_parse_receipts():
    user = SMTP_CONFIG["user"]
    password = SMTP_CONFIG["password"]
    imap_url = "imap.gmail.com"

    processed_ids = _load_processed_ids()
    new_expenses_count = 0

    try:
        mail = imaplib.IMAP4_SSL(imap_url)
        mail.login(user, password)
        mail.select("inbox")

        # Search for common receipt keywords received TODAY
        today_imap = datetime.now().strftime("%d-%b-%Y")
        # IMAP SINCE search is "on or after". Combining with keywords.
        search_query = f'SINCE {today_imap} (OR (OR (OR (FROM "amazon.com") (FROM "kellyspicers.com")) (FROM "grimco.com")) (OR (SUBJECT "Order Confirmation") (SUBJECT "Receipt")))'
        status, messages = mail.search(None, search_query)

        if status != "OK":
            return 0

        for msg_id in messages[0].split():
            # Use X-GM-MSGID to uniquely identify emails in Gmail
            res, msg_data = mail.fetch(msg_id, '(X-GM-MSGID RFC822)')
            
            gmail_msg_id = None
            raw_email = None

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Extract Gmail Message ID
                    data_header = response_part[0].decode('utf-8', errors='ignore')
                    msgid_match = re.search(r'X-GM-MSGID\s+(\d+)', data_header)
                    if msgid_match:
                        gmail_msg_id = msgid_match.group(1)
                    raw_email = response_part[1]

            if not gmail_msg_id or gmail_msg_id in processed_ids:
                continue

            msg = email.message_from_bytes(raw_email)
            
            # Extract Subject
            subject_parts = decode_header(msg["Subject"])
            subject = ""
            for part, encoding in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(encoding or "utf-8", errors="ignore")
                else:
                    subject += str(part)
            
            # Extract Date
            date_tuple = email.utils.parsedate_tz(msg["Date"])
            if date_tuple:
                msg_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple)).date()
            else:
                msg_date = datetime.now().date()

            # Extract Body and PDF Attachments
            body = ""
            pdf_texts = []
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain":
                        body += part.get_payload(decode=True).decode(errors='ignore')
                    elif content_type == "text/html":
                        body += clean_html(part.get_payload(decode=True).decode(errors='ignore'))
                    elif content_type == "application/pdf" or (".pdf" in content_disposition.lower()):
                        pdf_data = part.get_payload(decode=True)
                        if pdf_data:
                            pdf_texts.append(extract_text_from_pdf(pdf_data))
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
                if msg.get_content_type() == "text/html":
                    body = clean_html(body)

            # Combine all text to search for the amount
            full_search_text = body + "\n" + "\n".join(pdf_texts)

            # Determine Vendor
            from_header = msg.get("From", "").lower()
            vendor = "Unknown Vendor"
            if "amazon" in from_header:
                vendor = "Amazon"
            elif "staples" in from_header:
                vendor = "Staples"
            elif "uline" in from_header:
                vendor = "Uline"
            elif "kellyspicers" in from_header:
                vendor = "Kellypaper"
            elif "grimco" in from_header:
                vendor = "Grimco"
            
            amount = extract_amount(full_search_text)
            if amount:
                spending_service.add_spending(
                    target_date=msg_date,
                    vendor=vendor,
                    description=f"Auto-extracted: {subject}",
                    amount=amount,
                    source_id=gmail_msg_id
                )
                _save_processed_id(gmail_msg_id)
                new_expenses_count += 1

        mail.close()
        mail.logout()
        return new_expenses_count

    except Exception as e:
        print(f"Error fetching receipts: {e}")
        return 0
