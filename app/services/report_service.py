from datetime import date
import psycopg2.extras
from app.db.database import get_conn
from app.services import hide_service, settings_service

def get_report_data(target_date=None):
    if target_date is None:
        target_date = date.today()
    
    settings = settings_service.load_settings()
    excluded_accounts = settings.get("excluded_paid_accounts", [])
    
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Fetch hidden invoices for the target date
    hidden_list = hide_service.get_hidden_invoices_by_date(target_date)

    # 1. New Today (Invoices created today)
    cur.execute("""
        SELECT ib.invoicenumber, ib.name as job_name, ib.grandtotal, ib.ordereddate, ib.wanteddate, 
               ib.status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        WHERE DATE(ib.ordereddate) = %s AND ib.isdeleted = false AND ib.voided = false
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    new_today = cur.fetchall()

    # 2. In Progress (Ready is false, Picked up is false, and it's not a new invoice today)
    cur.execute("""
        SELECT ib.invoicenumber, ib.name as job_name, ib.grandtotal, ib.ordereddate, ib.wanteddate, 
               ib.status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        WHERE ib.onpendinglist = true 
        AND ib.readytopickup = false 
        AND DATE(ib.ordereddate) < %s
        AND ib.isdeleted = false AND ib.voided = false
        ORDER BY ib.wanteddate ASC
    """, (target_date,))
    in_progress = cur.fetchall()

    # 3. Ready for Pickup
    cur.execute("""
        SELECT ib.invoicenumber, ib.name as job_name, ib.grandtotal, ib.ordereddate, ib.wanteddate, 
               ib.status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        WHERE ib.readytopickup = true 
        AND ib.onpendinglist = true
        AND ib.isdeleted = false AND ib.voided = false
        ORDER BY ib.wanteddate ASC
    """, ())
    ready = cur.fetchall()

    # 4. Picked Up / Delivered Today
    cur.execute("""
        SELECT ib.invoicenumber, ib.name as job_name, ib.grandtotal, ib.ordereddate, ib.wanteddate, 
               ib.offpendingdate, ib.pickupdate, ib.locationchangedate,
               ib.status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        WHERE ib.isdeleted = false AND ib.voided = false
        AND (DATE(ib.pickupdate) = %s OR (ib.onpendinglist = false AND DATE(ib.offpendingdate) = %s))
        ORDER BY ib.invoicenumber DESC
    """, (target_date, target_date))
    picked_up = cur.fetchall()

    # 5. Paid Today (Aggregate direct payments + Parse consolidated AR payments)
    # We look for:
    # a) All payment/deposit records (type 2, 7) from today
    # b) All jobs posted today (type 1) that were not 'Charge' - this helps split batch payments
    cur.execute(f"""
        SELECT 
            ah.invoicenumber, 
            ah.name as record_name,
            ah.recordtype,
            COALESCE(ah.finalpaypaymethod, ah.partialpaypaymethod, tdr.paymode) as pay_method,
            CASE 
                WHEN ah.recordtype = '1' THEN ah.total 
                ELSE ABS(ah.total) 
            END as transaction_amount,
            ib.name as job_name, 
            ib.ordereddate,
            ib.wanteddate,
            ib.offpendingdate,
            ib.grandtotal,
            TRIM(CONCAT(p_con.firstname, ' ', p_con.lastname)) as contact_name,
            TRIM(a.title) as account_name,
            -- Indicators for aggregation
            CASE WHEN ah.recordtype = '7' THEN 1 ELSE 0 END as is_deposit,
            CASE WHEN ah.recordtype = '2' THEN 1 ELSE 0 END as is_payment,
            CASE WHEN ah.recordtype = '1' THEN 1 ELSE 0 END as is_job_posted
        FROM accounthistorydata ah
        LEFT JOIN tapedepositrecord tdr ON ah.invoicenumber = tdr.invoicenumber AND ah.recordtype = '7'
        LEFT JOIN invoicebase ib ON ah.invoicenumber = ib.invoicenumber AND ib.isdeleted = false AND ib.voided = false
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p_con ON c.id = p_con.id
        LEFT JOIN account a ON ib.account_id = a.id
        WHERE ah.isdeleted = false
        AND ah.recordtype IN ('1', '2', '7')
        AND COALESCE(ah.finalpaypaymethod, ah.partialpaypaymethod, tdr.paymode, '') != 'Charge'
        AND DATE(ah.posteddate) = %s
        ORDER BY ah.posteddate DESC, ah.recordtype DESC
    """, (target_date,))
    raw_paid = cur.fetchall()

    cur.close()
    conn.close()

    def process_rows(rows):
        res = []
        for r in rows:
            if str(r.get('invoicenumber')) in hidden_list:
                continue
            d = dict(r)

            # Use locationchangedate if pickupdate is missing
            if not d.get("pickupdate") and d.get("locationchangedate"):
                d["pickupdate"] = d["locationchangedate"]

            # Payment Status Logic
            total = round(float(d.get("grandtotal", 0) or 0), 2)
            paid = round(float(d.get("amount_paid", 0) or 0), 2)

            if total > 0 and paid >= total:
                d["payment_status"] = "PAID"
            elif paid > 0:
                balance = total - paid
                d["payment_status"] = f"BAL DUE: ${balance:,.2f}"
            else:
                d["payment_status"] = None

            acc = (d.get("account_name") or "").strip()
            con = (d.get("contact_name") or "").strip()
            
            d["account_display"] = acc if acc else con
            d["contact_display"] = con if acc else ""
            res.append(d)
        return res

    import re
    def process_paid_rows(rows):
        aggregated = {}
        
        conn_detail = get_conn()
        cur_detail = conn_detail.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        for r in rows:
            # Extract Invoice Numbers
            inv_nums = []
            is_generic_ar = False
            if r.get("invoicenumber"):
                inv_nums.append(str(r["invoicenumber"]))
            else:
                # Parse Payment(123,456) pattern
                match = re.search(r"Payment\((.*?)\)", str(r.get("record_name") or ""))
                if match:
                    inv_nums = [n.strip() for n in match.group(1).split(",")]
                    is_generic_ar = True
            
            if not inv_nums: continue

            pay_method = (r.get("pay_method") or "N/A").strip()

            for inv in inv_nums:
                if inv in hidden_list: continue
                
                if inv not in aggregated:
                    # Fetch basic details for this specific invoice
                    cur_detail.execute(f"""
                        SELECT ib.name, ib.ordereddate, ib.wanteddate, ib.offpendingdate,
                               ib.grandtotal,
                               TRIM(a.title) as account_name, 
                               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name
                        FROM invoicebase ib
                        JOIN invoice i ON ib.id = i.id
                        LEFT JOIN account a ON ib.account_id = a.id
                        LEFT JOIN contact c ON ib.contact_id = c.id
                        LEFT JOIN party p ON c.id = p.id
                        WHERE ib.invoicenumber = %s AND ib.isdeleted = false
                        LIMIT 1
                    """, (inv,))
                    det = cur_detail.fetchone()
                    
                    job_name = det["name"] if det else (r.get("job_name") or "Linked AR Invoice")
                    acc_disp = (det["account_name"] or det["contact_name"]) if det else (r.get("account_name") or r.get("contact_name") or "-")
                    con_disp = (det["contact_name"] if det["account_name"] else "") if det else (r.get("contact_name") if r.get("account_name") else "")
                    
                    aggregated[inv] = {
                        "invoicenumber": inv,
                        "job_name": job_name,
                        "ordereddate": det["ordereddate"] if det else r.get("ordereddate"),
                        "wanteddate": det["wanteddate"] if det else r.get("wanteddate"),
                        "offpendingdate": det["offpendingdate"] if det else r.get("offpendingdate"),
                        "grandtotal": 0, # This will store "Today's Payment Amount"
                        "invoice_total": float(det["grandtotal"] or 0) if det else 0,
                        "account_display": acc_disp.strip(),
                        "contact_display": con_disp.strip(),
                        "is_deposit": 0,
                        "is_payment": 0,
                        "is_job_posted": 0,
                        "is_ar": False,
                        "pay_methods": set()
                    }
                
                # Accumulate flags
                if is_generic_ar: aggregated[inv]["is_ar"] = True
                if r.get("is_deposit"): aggregated[inv]["is_deposit"] = 1
                if r.get("is_payment"): aggregated[inv]["is_payment"] = 1
                if r.get("is_job_posted"): aggregated[inv]["is_job_posted"] = 1
                
                if pay_method and pay_method != "N/A":
                    aggregated[inv]["pay_methods"].add(pay_method)

                # Amount logic:
                if r.get("is_job_posted"):
                    # If the job was posted today, we show its total value as 'paid today' 
                    # ONLY IF we haven't already captured a specific payment today.
                    if aggregated[inv]["grandtotal"] == 0:
                        aggregated[inv]["grandtotal"] = float(r["transaction_amount"] or 0)
                else:
                    # If this is a real cash transaction (Payment or Deposit)
                    # We check the specific allocation records for THIS invoice
                    cur_detail.execute("SELECT SUM(totalpay) FROM tapeinvoicepayrecord WHERE invoicenumber = %s AND isdeleted = false", (inv,))
                    tip = float(cur_detail.fetchone()['sum'] or 0)
                    cur_detail.execute("SELECT SUM(totaldeposits) FROM tapedepositappliedrecord WHERE invoicenumber = %s AND isdeleted = false", (inv,))
                    tda = float(cur_detail.fetchone()['sum'] or 0)
                    cur_detail.execute("SELECT SUM(amountpaid) FROM tapesalerecord WHERE invoicenumber = %s AND isdeleted = false AND paymode != 'Charge'", (inv,))
                    tsr = float(cur_detail.fetchone()['sum'] or 0)
                    
                    actual_paid_for_this_inv = tip + tda + tsr
                    
                    if actual_paid_for_this_inv > 0:
                        aggregated[inv]["grandtotal"] = actual_paid_for_this_inv
                    else:
                        # Fallback for generic AR payments that don't have allocation records
                        if len(inv_nums) == 1:
                            aggregated[inv]["grandtotal"] = float(r["transaction_amount"] or 0)
                        elif aggregated[inv]["grandtotal"] == 0:
                            aggregated[inv]["grandtotal"] = aggregated[inv]["invoice_total"]

        # Final pass for each aggregated invoice to check balance and transaction type
        res = []
        target_date_str = str(target_date)
        for inv, d in aggregated.items():
            if d.get("account_display") in excluded_accounts: continue

            # Robust balance calculation using Tape records
            cur_detail.execute("SELECT SUM(totalpay) FROM tapeinvoicepayrecord WHERE invoicenumber = %s AND isdeleted = false", (inv,))
            tip = float(cur_detail.fetchone()['sum'] or 0)
            cur_detail.execute("SELECT SUM(totaldeposits) FROM tapedepositappliedrecord WHERE invoicenumber = %s AND isdeleted = false", (inv,))
            tda = float(cur_detail.fetchone()['sum'] or 0)
            cur_detail.execute("SELECT SUM(amountpaid) FROM tapesalerecord WHERE invoicenumber = %s AND isdeleted = false AND paymode != 'Charge'", (inv,))
            tsr = float(cur_detail.fetchone()['sum'] or 0)
            
            total_paid_ever = tip + tda + tsr
            grand_total = d["invoice_total"]
            
            # Remaining Balance
            display_balance = max(0, grand_total - total_paid_ever)
            is_partial = display_balance > 0.01 and total_paid_ever > 0
            
            d["current_balance"] = display_balance
            d["is_partial"] = is_partial

            # Check if invoice was finalized (posted) today
            is_finalized_today = False
            if d.get("offpendingdate"):
                post_date = d["offpendingdate"]
                post_date_str = post_date.strftime('%Y-%m-%d') if hasattr(post_date, 'strftime') else str(post_date).split('T')[0]
                if post_date_str == target_date_str: is_finalized_today = True

            # Transaction Type Label
            if d.get("is_ar"): d["transaction_type"] = "AR PAYMENT"
            elif d.get("is_payment") or is_finalized_today: d["transaction_type"] = "PAID"
            elif d.get("is_deposit"): d["transaction_type"] = "DEPOSIT"
            else: d["transaction_type"] = "PAID"
            
            d["pay_method_display"] = ", ".join(sorted([m for m in d["pay_methods"] if m and m != "N/A"]))
            if not d["pay_method_display"]: d["pay_method_display"] = "N/A"
            res.append(d)

        cur_detail.close()
        conn_detail.close()
        return sorted(res, key=lambda x: x["invoicenumber"], reverse=True)

    return {
        "date": str(target_date),
        "new_today": process_rows(new_today),
        "in_progress": process_rows(in_progress),
        "ready": process_rows(ready),
        "picked_up": process_rows(picked_up),
        "paid": process_paid_rows(raw_paid)
    }
