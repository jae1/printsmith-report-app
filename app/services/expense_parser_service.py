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
        r"(?:Order Total|Total|Grand Total|Amount Paid|TOTAL DUE|Invoice Total|AMT DUE)[:\s]*\$?\s*([\d,]+\.\d{2})",
        r"Total\s*Amount\s*[:\s]*\$?\s*([\d,]+\.\d{2})",
        r"TOTAL[:\s]+\s*([\d,]+\.\d{2})",
        r"\$\s*([\d,]+\.\d{2})"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
    return None

def extract_card(text):
    """
    Attempt to extract the last 4 digits of the card used.
    """
    patterns = [
        r"(?:Visa|Mastercard|Amex|Discover|Card|Account)[:\s*]*[\*xX\-]*(\d{4})",
        r"(?:ending in|ending with)[:\s]*(\d{4})",
        r"\*{12}(\d{4})"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
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

def summarize_items(text, vendor):
    """
    Attempt to extract a brief summary of what was purchased.
    """
    text_lower = text.lower()
    
    # Kelly Paper specific
    if vendor == "Kelly Paper":
        if "lamination" in text_lower or "pouch" in text_lower:
            return "Lamination Pouches"
        if "paper" in text_lower or "bond" in text_lower or "cover" in text_lower:
            return "Paper Stock"
        if "ink" in text_lower or "toner" in text_lower:
            return "Ink/Toner"

    # USPS specific
    if vendor == "USPS":
        if "click-n-ship" in text_lower or "shipping label" in text_lower:
            return "Shipping Label"
        return "Postage/Shipping"

    # Amazon specific
    if vendor == "Amazon":
        items = []
        if "ink" in text_lower: items.append("Ink")
        if "paper" in text_lower: items.append("Paper")
        if "label" in text_lower: items.append("Labels")
        if "tape" in text_lower: items.append("Tape")
        if items: return f"Office Supplies: {', '.join(items)}"
        return "Amazon Purchase"

    # Grimco
    if vendor == "Grimco":
        if "vinyl" in text_lower: return "Vinyl Materials"
        if "ink" in text_lower: return "Large Format Ink"
        return "Sign Supplies"

    return "General Supplies"

def fetch_and_parse_receipts():
    user = SMTP_CONFIG["user"]
    password = SMTP_CONFIG["password"]
    imap_url = "imap.gmail.com"

    processed_ids = _load_processed_ids()
    # Get current today's spending to check for duplicates even if processed_id is missing
    target_date_today = datetime.now().date()
    today_spending = spending_service.get_spending_by_date(target_date_today)
    
    new_expenses_count = 0
    print(f"DEBUG: Starting sync for {target_date_today}...")

    try:
        mail = imaplib.IMAP4_SSL(imap_url)
        mail.login(user, password)
        mail.select("inbox")

        today_imap = datetime.now().strftime("%d-%b-%Y")
        # Added usps.com and Payment Confirmation to keywords
        search_query = f'SINCE {today_imap} (OR (OR (OR (OR (FROM "amazon.com") (FROM "kellyspicers.com")) (FROM "grimco.com")) (FROM "usps.com")) (OR (OR (SUBJECT "Order Confirmation") (SUBJECT "Receipt")) (SUBJECT "Payment Confirmation")))'
        status, messages = mail.search(None, search_query)

        if status != "OK" or not messages[0]:
            print("DEBUG: No matching emails found today.")
            mail.logout()
            return 0

        msg_list = messages[0].split()
        print(f"DEBUG: Found {len(msg_list)} candidate emails today.")

        for msg_id in msg_list:
            res, msg_data = mail.fetch(msg_id, '(X-GM-MSGID RFC822)')
            gmail_msg_id = None
            raw_email = None

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    data_header = response_part[0].decode('utf-8', errors='ignore')
                    msgid_match = re.search(r'X-GM-MSGID\s+(\d+)', data_header)
                    if msgid_match:
                        gmail_msg_id = msgid_match.group(1)
                    raw_email = response_part[1]

            if not gmail_msg_id: continue
            
            msg = email.message_from_bytes(raw_email)
            subject_parts = decode_header(msg["Subject"])
            subject = ""
            for part, encoding in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(encoding or "utf-8", errors="ignore")
                else:
                    subject += str(part)

            print(f"DEBUG: Checking Email ID {gmail_msg_id} | Subject: {subject}")

            # SELF-HEALING: If it's in processed_ids but NOT in today's spending, allow re-sync
            is_already_in_spending = any(str(s.get("source_id")) == str(gmail_msg_id) for s in today_spending)
            
            if gmail_msg_id in processed_ids and is_already_in_spending:
                print(f"DEBUG: Skipping {gmail_msg_id} (Already processed and exists in spending)")
                continue

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

            full_search_text = body + "\n" + "\n".join(pdf_texts)
            from_header = msg.get("From", "").lower()
            
            vendor = "Unknown Vendor"
            if "amazon" in from_header: vendor = "Amazon"
            elif "staples" in from_header: vendor = "Staples"
            elif "uline" in from_header: vendor = "Uline"
            elif "kellyspicers" in from_header or "kelly paper" in from_header.lower(): vendor = "Kelly Paper"
            elif "grimco" in from_header: vendor = "Grimco"
            elif "usps.com" in from_header: vendor = "USPS"
            
            amount = extract_amount(full_search_text)
            if amount:
                # Generate a better description
                item_summary = summarize_items(full_search_text, vendor)
                detailed_desc = f"{item_summary} ({subject})"
                
                # Extract Card Info
                card_last_4 = extract_card(full_search_text)
                
                print(f"DEBUG: Successfully extracted ${amount} for {vendor} - {item_summary} (Card: {card_last_4})")
                spending_service.add_spending(
                    target_date=msg_date,
                    vendor=vendor,
                    description=detailed_desc,
                    amount=amount,
                    source_id=gmail_msg_id,
                    card=card_last_4
                )
                _save_processed_id(gmail_msg_id)
                new_expenses_count += 1
            else:
                print(f"DEBUG: Could not extract amount for {subject}")

        mail.close()
        mail.logout()
        print(f"DEBUG: Sync complete. Added {new_expenses_count} items.")
        return new_expenses_count

    except Exception as e:
        print(f"Error fetching receipts: {e}")
        return 0
