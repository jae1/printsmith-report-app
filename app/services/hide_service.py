import json
import os

HIDDEN_FILE = "hidden_invoices.json"

def get_hidden_invoices():
    if not os.path.exists(HIDDEN_FILE):
        return []
    try:
        with open(HIDDEN_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def hide_invoice(invoice_number):
    hidden = set(get_hidden_invoices())
    hidden.add(str(invoice_number))
    with open(HIDDEN_FILE, "w") as f:
        json.dump(list(hidden), f)

def unhide_invoice(invoice_number):
    hidden = set(get_hidden_invoices())
    hidden.discard(str(invoice_number))
    with open(HIDDEN_FILE, "w") as f:
        json.dump(list(hidden), f)
