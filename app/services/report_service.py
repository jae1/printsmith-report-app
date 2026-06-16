from datetime import date
import psycopg2.extras
from app.db.database import get_conn
from app.services import hide_service, settings_service

def get_report_data(target_date=None):
    if target_date is None:
        target_date = date.today()

    hidden_list = hide_service.get_all_hidden_invoices()
    settings = settings_service.load_settings()
    excluded_accounts = settings.get("excluded_paid_accounts", [])

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    select_fields = """
        ib.invoicenumber, 
        ib.name as job_name, 
        ib.ordereddate, 
        ib.wanteddate, 
        ib.pickupdate,
        ib.locationchangedate,
        ib.grandtotal,
        TRIM(CONCAT(p_con.firstname, ' ', p_con.lastname)) as contact_name,
        TRIM(a.title) as account_name,
        dl.name as status,
        COALESCE(tsr_sum.paid_total, 0) as amount_paid
    """
    
    join_tables = """
        LEFT JOIN estimate e ON ib.id = e.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p_con ON c.id = p_con.id
        LEFT JOIN account a ON ib.account_id = a.id
        LEFT JOIN productionlocations dl ON ib.documentlocation_id = dl.id
        LEFT JOIN (
            SELECT invoicenumber, SUM(paid_amount) as paid_total
            FROM (
                SELECT invoicenumber, total as paid_amount 
                FROM tapesalerecord 
                WHERE isdeleted = false AND paymode != 'Charge'
                UNION ALL
                SELECT invoicenumber, totaldeposits as paid_amount 
                FROM tapedepositappliedrecord 
                WHERE isdeleted = false
            ) all_payments
            GROUP BY invoicenumber
        ) tsr_sum ON ib.invoicenumber = tsr_sum.invoicenumber
    """

    # 1. New Today
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND ib.voided = false
        AND e.id IS NULL
        AND DATE(ib.ordereddate) = %s
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    new_today = cur.fetchall()

    # 2. In Progress
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND ib.voided = false
        AND e.id IS NULL
        AND ib.onpendinglist = true
        AND (ib.offpendingdate IS NULL OR ib.offpendingdate::text = '')
        AND (ib.documentlocation_id IS NULL OR ib.documentlocation_id NOT IN (1153, 1158, 3221, 3226, 3227, 3228))
        AND ib.readytopickup = false
        AND COALESCE(ib.wanteddate, ib.ordereddate) >= %s - INTERVAL '6 MONTH'
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    in_progress = cur.fetchall()

    # 3. Ready for Pickup
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND ib.voided = false
        AND e.id IS NULL
        AND (ib.documentlocation_id IN (1158, 3226, 3227, 3228) OR ib.readytopickup = true)
        AND (ib.documentlocation_id IS NULL OR ib.documentlocation_id NOT IN (1153, 3221))
        AND (ib.offpendingdate IS NULL OR ib.offpendingdate::text = '')
        AND (ib.pickupdate IS NULL OR ib.pickupdate::text = '')
        AND COALESCE(ib.wanteddate, ib.ordereddate) >= %s - INTERVAL '1 MONTH'
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    ready = cur.fetchall()

    # 4. Picked Up / Delivered Today
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND ib.voided = false
        AND e.id IS NULL
        AND (
            (ib.pickupdate IS NOT NULL AND ib.pickupdate::text != '' AND DATE(ib.pickupdate) = %s)
            OR 
            (ib.documentlocation_id IN (1153, 3221) AND DATE(ib.locationchangedate) = %s)
        )
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
        handled_by_type1 = set()
        
        # 1. First pass: Identify all jobs posted (finalized) today that were paid
        for r in rows:
            if r.get("is_job_posted") and r.get("invoicenumber"):
                inv = str(r["invoicenumber"])
                if inv in hidden_list: continue
                
                handled_by_type1.add(inv)
                
                if inv not in aggregated:
                    aggregated[inv] = {
                        "invoicenumber": inv,
                        "job_name": r.get("job_name") or "Job Posted Today",
                        "ordereddate": r.get("ordereddate"),
                        "wanteddate": r.get("wanteddate"),
                        "offpendingdate": r.get("offpendingdate"),
                        "grandtotal": 0,
                        "account_display": (r.get("account_name") or r.get("contact_name") or "").strip() or "-",
                        "contact_display": r.get("contact_name") if r.get("account_name") else "",
                        "is_deposit": 0,
                        "is_payment": 1,
                        "is_ar": False,
                        "pay_methods": set()
                    }
                aggregated[inv]["grandtotal"] += float(r["transaction_amount"] or 0)
                if r.get("pay_method"):
                    aggregated[inv]["pay_methods"].add(r["pay_method"])

        # 2. Second pass: Handle AR payments and deposits, avoiding double counting
        conn_detail = get_conn()
        cur_detail = conn_detail.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        for r in rows:
            if r.get("is_job_posted"): continue # Already handled
            
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
                
                # IMPORTANT: If this invoice was already handled as a 'job posted today', 
                # we only update the pay method, not the amount (to avoid double counting).
                if inv in handled_by_type1:
                    if pay_method != "N/A":
                        aggregated[inv]["pay_methods"].add(pay_method)
                    continue

                # Handle AR payment or Deposit on an existing job
                if inv not in aggregated:
                    # Fetch details for this specific invoice
                    cur_detail.execute(f"""
                        SELECT ib.name, ib.ordereddate, ib.wanteddate, ib.offpendingdate,
                               ib.grandtotal,
                               TRIM(a.title) as account_name, 
                               TRIM(CONCAT(p.firstname, ' ', p.lastname)) as contact_name
                        FROM invoicebase ib
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
                        "account_display": acc_disp.strip(),
                        "contact_display": con_disp.strip(),
                        "is_deposit": 0,
                        "is_payment": 0,
                        "is_ar": is_generic_ar,
                        "pay_methods": set()
                    }
                
                aggregated[inv]["pay_methods"].add(pay_method)

                if r.get("invoicenumber"): # Direct payment record
                    aggregated[inv]["grandtotal"] += float(r["transaction_amount"] or 0)
                else: # Consolidated AR payment - use the invoice total as PrintSmith doesn't break it down
                    if aggregated[inv]["grandtotal"] == 0:
                        cur_detail.execute("SELECT grandtotal FROM invoicebase WHERE invoicenumber = %s", (inv,))
                        det = cur_detail.fetchone()
                        if det:
                            aggregated[inv]["grandtotal"] = float(det["grandtotal"] or 0)
                
                aggregated[inv]["is_deposit"] = max(aggregated[inv]["is_deposit"], r["is_deposit"])
                aggregated[inv]["is_payment"] = max(aggregated[inv]["is_payment"], r["is_payment"])

                # Calculate current balance for this invoice
                cur_detail.execute("SELECT SUM(total) as balance FROM accounthistorydata WHERE invoicenumber = %s AND isdeleted = false", (inv,))
                bal_res = cur_detail.fetchone()
                current_balance = float(bal_res["balance"] or 0)
                
                # If balance is very small (rounding), treat as 0
                if abs(current_balance) < 0.01: current_balance = 0

                aggregated[inv]["current_balance"] = current_balance
                aggregated[inv]["is_partial"] = current_balance > 0.01

        cur_detail.close()
        conn_detail.close()

        # Final Formatting
        res = []
        target_date_str = str(target_date)
        for inv, d in aggregated.items():
            # Skip excluded accounts
            if d.get("account_display") in excluded_accounts:
                continue

            # Check if invoice was finalized (posted) today
            is_finalized_today = False
            if d.get("offpendingdate"):
                post_date = d["offpendingdate"]
                if hasattr(post_date, 'strftime'):
                    post_date_str = post_date.strftime('%Y-%m-%d')
                else:
                    post_date_str = str(post_date).split('T')[0]
                
                if post_date_str == target_date_str:
                    is_finalized_today = True

            # Transaction Type Label
            if d.get("is_ar"):
                d["transaction_type"] = "AR PAYMENT"
            elif d.get("is_partial"):
                d["transaction_type"] = "PARTIAL"
            elif d.get("is_payment") or is_finalized_today:
                d["transaction_type"] = "PAID"
            elif d.get("is_deposit"):
                d["transaction_type"] = "DEPOSIT"
            else:
                d["transaction_type"] = "PAID"
            
            d["pay_method_display"] = ", ".join(sorted([m for m in d["pay_methods"] if m and m != "N/A"]))
            if not d["pay_method_display"]: d["pay_method_display"] = "N/A"
            res.append(d)
        
        return sorted(res, key=lambda x: x["invoicenumber"], reverse=True)

    return {
        "date": str(target_date),
        "new_today": process_rows(new_today),
        "in_progress": process_rows(in_progress),
        "ready": process_rows(ready),
        "picked_up": process_rows(picked_up),
        "paid": process_paid_rows(raw_paid)
    }
