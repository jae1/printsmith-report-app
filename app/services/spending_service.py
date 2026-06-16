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

def add_spending(target_date, vendor, description, amount, source_id=None):
    data = _load_spending()
    date_str = str(target_date)
    if date_str not in data:
        data[date_str] = []
    
    data[date_str].append({
        "id": os.urandom(4).hex(), # Simple random ID for deletion
        "vendor": vendor,
        "description": description,
        "amount": float(amount),
        "source_id": source_id
    })
    _save_spending(data)

def delete_spending(target_date, spending_id):
    data = _load_spending()
    date_str = str(target_date)
    source_id = None
    if date_str in data:
        new_list = []
        for s in data[date_str]:
            if s["id"] == spending_id:
                source_id = s.get("source_id")
            else:
                new_list.append(s)
        data[date_str] = new_list
        if not data[date_str]:
            del data[date_str]
        _save_spending(data)
    return source_id

def update_spending(target_date, spending_id, vendor):
    data = _load_spending()
    date_str = str(target_date)
    if date_str in data:
        for s in data[date_str]:
            if s["id"] == spending_id:
                s["vendor"] = vendor
                break
        _save_spending(data)

def get_unique_vendors():
    data = _load_spending()
    vendors = set()
    for date_records in data.values():
        for record in date_records:
            if "vendor" in record and record["vendor"].strip():
                vendors.add(record["vendor"].strip())
    return sorted(list(vendors))
