import json
import os
from datetime import date

SPENDING_FILE = "daily_spending.json"

def _load_spending():
    if not os.path.exists(SPENDING_FILE):
        return {}
    try:
        with open(SPENDING_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def _save_spending(data):
    with open(SPENDING_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_spending_by_date(target_date):
    data = _load_spending()
    return data.get(str(target_date), [])

def add_spending(target_date, vendor, description, amount):
    data = _load_spending()
    date_str = str(target_date)
    if date_str not in data:
        data[date_str] = []
    
    data[date_str].append({
        "id": os.urandom(4).hex(), # Simple random ID for deletion
        "vendor": vendor,
        "description": description,
        "amount": float(amount)
    })
    _save_spending(data)

def delete_spending(target_date, spending_id):
    data = _load_spending()
    date_str = str(target_date)
    if date_str in data:
        data[date_str] = [s for s in data[date_str] if s["id"] != spending_id]
        _save_spending(data)

def get_unique_vendors():
    data = _load_spending()
    vendors = set()
    for date_records in data.values():
        for record in date_records:
            if "vendor" in record and record["vendor"].strip():
                vendors.add(record["vendor"].strip())
    return sorted(list(vendors))
