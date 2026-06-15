import json
import os
import psycopg2.extras
from app.db.database import get_conn

HIDDEN_FILE = "hidden_invoices.json"

def get_hidden_data():
    if not os.path.exists(HIDDEN_FILE):
        return {}
    try:
        with open(HIDDEN_FILE, "r") as f:
            data = json.load(f)
            # Migration: if old flat format, clear it to avoid issues
            if not isinstance(data, dict):
                return {}
            # Migration: check if values are list (date-mapped format)
            first_val = next(iter(data.values()), None)
            if first_val is not None and not isinstance(first_val, list):
                # This was the flatten format we just made, convert back
                return {} 
            return data
    except:
        return {}

def get_all_hidden_invoices():
    """Returns all hidden invoice numbers across all dates for filtering."""
    data = get_hidden_data()
    all_invs = set()
    for inv_list in data.values():
        for inv in inv_list:
            all_invs.add(str(inv))
    return list(all_invs)

def get_hidden_invoices_by_date(target_date):
    """Returns hidden invoices for a specific date (for manager UI)."""
    data = get_hidden_data()
    return data.get(str(target_date), [])

def hide_invoice(target_date, invoice_number):
    data = get_hidden_data()
    date_str = str(target_date)
    if date_str not in data:
        data[date_str] = []
    
    hidden_set = set(data[date_str])
    hidden_set.add(str(invoice_number))
    data[date_str] = list(hidden_set)
    
    with open(HIDDEN_FILE, "w") as f:
        json.dump(data, f, indent=4)

def unhide_invoice(target_date, invoice_number):
    data = get_hidden_data()
    date_str = str(target_date)
    if date_str in data:
        hidden_set = set(data[date_str])
        hidden_set.discard(str(invoice_number))
        data[date_str] = list(hidden_set)
        if not data[date_str]:
            del data[date_str]
            
        with open(HIDDEN_FILE, "w") as f:
            json.dump(data, f, indent=4)

def get_hidden_details(target_date):
    hidden_list = get_hidden_invoices_by_date(target_date)
    if not hidden_list:
        return []
    
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                ib.invoicenumber, 
                ib.name as job_name, 
                ib.grandtotal,
                TRIM(CONCAT(p_con.firstname, ' ', p_con.lastname)) as contact_name,
                TRIM(a.title) as account_name
            FROM invoicebase ib
            LEFT JOIN contact c ON ib.contact_id = c.id
            LEFT JOIN party p_con ON c.id = p_con.id
            LEFT JOIN account a ON ib.account_id = a.id
            WHERE ib.invoicenumber = ANY(%s)
            ORDER BY ib.invoicenumber DESC
        """, (hidden_list,))
        rows = cur.fetchall()
        
        res = []
        for r in rows:
            d = dict(r)
            acc = (d.get("account_name") or "").strip()
            con = (d.get("contact_name") or "").strip()
            d["account_display"] = acc if acc else con
            d["contact_display"] = con if acc else ""
            res.append(d)
        return res
    except Exception as e:
        print(f"Error fetching hidden details: {e}")
        return []
    finally:
        cur.close()
        conn.close()
