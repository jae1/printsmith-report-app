from datetime import date, timedelta
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
               pl.name as status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        LEFT JOIN productionlocations pl ON ib.documentlocation_id = pl.id
        WHERE DATE(ib.ordereddate) = %s AND ib.isdeleted = false AND ib.voided = false
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    new_today = cur.fetchall()

    # 2. In Progress (Ready is false, Picked up is false, and it's not a new invoice today)
    cur.execute("""
        SELECT ib.invoicenumber, ib.name as job_name, ib.grandtotal, ib.ordereddate, ib.wanteddate, 
               pl.name as status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        LEFT JOIN productionlocations pl ON ib.documentlocation_id = pl.id
        WHERE ib.onpendinglist = true 
        AND ib.readytopickup = false 
        AND (pl.name IS NULL OR pl.name NOT IN ('Ready for Pickup', 'Ready for Delivery', 'Shipping', 'Complete'))
        AND DATE(ib.ordereddate) < %s
        AND ib.isdeleted = false AND ib.voided = false
        ORDER BY ib.wanteddate ASC
    """, (target_date,))
    in_progress = cur.fetchall()

    # 3. Ready for Pickup (Limit to 10 days before target_date)
    pickup_limit_date = target_date - timedelta(days=10)
    cur.execute("""
        SELECT ib.invoicenumber, ib.name as job_name, ib.grandtotal, ib.ordereddate, ib.wanteddate, 
               pl.name as status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        LEFT JOIN productionlocations pl ON ib.documentlocation_id = pl.id
        WHERE (ib.readytopickup = true OR pl.name IN ('Ready for Pickup', 'Ready for Delivery'))
        AND (pl.name IS NULL OR pl.name != 'Shipping')
        AND ib.onpendinglist = true
        AND DATE(ib.ordereddate) >= %s
        AND ib.isdeleted = false AND ib.voided = false
        ORDER BY ib.wanteddate ASC
    """, (pickup_limit_date,))
    ready = cur.fetchall()

    # 4. Picked Up / Delivered Today (Completed Today)
    cur.execute("""
        SELECT ib.invoicenumber, ib.name as job_name, ib.grandtotal, ib.ordereddate, ib.wanteddate, 
               ib.offpendingdate, ib.pickupdate, ib.locationchangedate,
               pl.name as status,
               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name,
               TRIM(a.title) as account_name
        FROM invoicebase ib
        JOIN invoice i ON ib.id = i.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p ON c.id = p.id
        LEFT JOIN account a ON ib.account_id = a.id
        LEFT JOIN productionlocations pl ON ib.documentlocation_id = pl.id
        WHERE ib.isdeleted = false AND ib.voided = false
        AND (
            DATE(ib.pickupdate) = %s 
            OR (ib.onpendinglist = false AND DATE(ib.offpendingdate) = %s)
            OR (pl.name = 'Shipping' AND DATE(ib.locationchangedate) = %s)
            OR (pl.name = 'Complete' AND DATE(ib.locationchangedate) = %s)
        )
        ORDER BY ib.invoicenumber DESC
    """, (target_date, target_date, target_date, target_date))
    picked_up = cur.fetchall()

    # 5. Paid Today (Aggregate direct payments + Parse consolidated AR payments)
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

            if not d.get("pickupdate") and d.get("locationchangedate"):
                d["pickupdate"] = d["locationchangedate"]

            total = round(float(d.get("grandtotal", 0) or 0), 2)
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
            inv_nums = []
            is_generic_ar = False
            if r.get("invoicenumber"):
                inv_nums.append(str(r["invoicenumber"]))
            else:
                match = re.search(r"Payment\((.*?)\)", str(r.get("record_name") or ""))
                if match:
                    inv_nums = [n.strip() for n in match.group(1).split(",")]
                    is_generic_ar = True
            
            if not inv_nums: continue
            pay_method = (r.get("pay_method") or "N/A").strip()

            for inv in inv_nums:
                if inv in hidden_list: continue
                if inv not in aggregated:
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
                        "grandtotal": 0,
                        "invoice_total": float(det["grandtotal"] or 0) if det else 0,
                        "account_display": acc_disp.strip(),
                        "contact_display": con_disp.strip(),
                        "is_deposit": 0,
                        "is_payment": 0,
                        "is_job_posted": 0,
                        "is_ar": False,
                        "pay_methods": set()
                    }
                
                if is_generic_ar: aggregated[inv]["is_ar"] = True
                if r.get("is_deposit"): aggregated[inv]["is_deposit"] = 1
                if r.get("is_payment"): aggregated[inv]["is_payment"] = 1
                if r.get("is_job_posted"): aggregated[inv]["is_job_posted"] = 1
                if pay_method and pay_method != "N/A":
                    aggregated[inv]["pay_methods"].add(pay_method)

                if r.get("is_job_posted"):
                    if aggregated[inv]["grandtotal"] == 0:
                        aggregated[inv]["grandtotal"] = float(r["transaction_amount"] or 0)
                else:
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
                        if len(inv_nums) == 1:
                            aggregated[inv]["grandtotal"] = float(r["transaction_amount"] or 0)
                        elif aggregated[inv]["grandtotal"] == 0:
                            aggregated[inv]["grandtotal"] = aggregated[inv]["invoice_total"]

        res = []
        target_date_str = str(target_date)
        for inv, d in aggregated.items():
            if d.get("account_display") in excluded_accounts: continue

            cur_detail.execute("SELECT SUM(totalpay) FROM tapeinvoicepayrecord WHERE invoicenumber = %s AND isdeleted = false", (inv,))
            tip = float(cur_detail.fetchone()['sum'] or 0)
            cur_detail.execute("SELECT SUM(totaldeposits) FROM tapedepositappliedrecord WHERE invoicenumber = %s AND isdeleted = false", (inv,))
            tda = float(cur_detail.fetchone()['sum'] or 0)
            cur_detail.execute("SELECT SUM(amountpaid) FROM tapesalerecord WHERE invoicenumber = %s AND isdeleted = false AND paymode != 'Charge'", (inv,))
            tsr = float(cur_detail.fetchone()['sum'] or 0)
            
            total_paid_ever = tip + tda + tsr
            grand_total = d["invoice_total"]
            display_balance = max(0, grand_total - total_paid_ever)
            is_partial = display_balance > 0.01 and total_paid_ever > 0
            
            d["current_balance"] = display_balance
            d["is_partial"] = is_partial

            # --- Check if there was actual money moved TODAY ---
            # We don't want to show an invoice in "Paid Today" if the only thing that happened today was posting,
            # and it was already fully paid via a deposit on a PREVIOUS day.
            actual_payment_today = d.get("is_payment", 0) > 0 or d.get("is_deposit", 0) > 0
            if not actual_payment_today and d.get("is_job_posted", 0) > 0:
                # Let's verify if there is ANY tapeinvoicepayrecord or tapesalerecord TODAY that is NOT just 'Deposit'
                cur_detail.execute("SELECT SUM(totalpay) FROM tapeinvoicepayrecord WHERE invoicenumber = %s AND DATE(date) = %s AND isdeleted = false AND method != 'Deposit'", (inv, target_date))
                tip_today = float(cur_detail.fetchone()['sum'] or 0)
                cur_detail.execute("SELECT SUM(amountpaid) FROM tapesalerecord WHERE invoicenumber = %s AND DATE(date) = %s AND isdeleted = false AND paymode != 'Charge' AND paymode != 'Deposit'", (inv, target_date))
                tsr_today = float(cur_detail.fetchone()['sum'] or 0)
                
                if tip_today + tsr_today <= 0:
                    # There is NO actual new money today. 
                    # It was likely fully pre-paid by a deposit yesterday, and just posted today.
                    continue

            is_finalized_today = False
            if d.get("offpendingdate"):
                post_date = d["offpendingdate"]
                post_date_str = post_date.strftime('%Y-%m-%d') if hasattr(post_date, 'strftime') else str(post_date).split('T')[0]
                if post_date_str == target_date_str: is_finalized_today = True

            if d.get("is_ar"): d["transaction_type"] = "AR PAYMENT"
            elif d.get("is_payment") or is_finalized_today: d["transaction_type"] = "PAID"
            elif d.get("is_deposit"): d["transaction_type"] = "DEPOSIT"
            else: d["transaction_type"] = "PAID"
            
            d["pay_method_display"] = ", ".join(sorted([m for m in d["pay_methods"] if m and m not in ("N/A", "Deposit")]))
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
