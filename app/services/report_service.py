from datetime import date
import psycopg2.extras
from app.db.database import get_conn
from app.services import hide_service

def get_report_data(target_date=None):
    if target_date is None:
        target_date = date.today()

    hidden_list = hide_service.get_hidden_invoices()

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    select_fields = """
        ib.invoicenumber, 
        ib.name as job_name, 
        ib.ordereddate, 
        ib.wanteddate, 
        ib.pickupdate,
        ib.grandtotal,
        TRIM(CONCAT(p_con.firstname, ' ', p_con.lastname)) as contact_name,
        TRIM(a.title) as account_name,
        dl.name as status
    """
    
    join_tables = """
        LEFT JOIN estimate e ON ib.id = e.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p_con ON c.id = p_con.id
        LEFT JOIN account a ON ib.account_id = a.id
        LEFT JOIN productionlocations dl ON ib.documentlocation_id = dl.id
    """

    # 1. 오늘 들어온 잡
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND e.id IS NULL
        AND DATE(ib.ordereddate) = %s
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    new_today = cur.fetchall()

    # 2. 진행중인 잡
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND e.id IS NULL
        AND ib.onpendinglist = true
        AND (ib.offpendingdate IS NULL OR ib.offpendingdate::text = '')
        AND (ib.documentlocation_id IS NULL OR ib.documentlocation_id NOT IN (1153, 1158, 3221, 3226, 3227, 3228))
        AND ib.readytopickup = false
        AND COALESCE(ib.wanteddate, ib.ordereddate) >= %s - INTERVAL '6 MONTH'
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    in_progress = cur.fetchall()

    # 3. 준비된 잡
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND e.id IS NULL
        AND (ib.documentlocation_id IN (1158, 3226, 3227, 3228) OR ib.readytopickup = true)
        AND (ib.documentlocation_id IS NULL OR ib.documentlocation_id NOT IN (1153, 3221))
        AND (ib.offpendingdate IS NULL OR ib.offpendingdate::text = '')
        AND (ib.pickupdate IS NULL OR ib.pickupdate::text = '')
        AND COALESCE(ib.wanteddate, ib.ordereddate) >= %s - INTERVAL '1 MONTH'
        ORDER BY ib.invoicenumber DESC
    """, (target_date,))
    ready = cur.fetchall()

    # 4. 오늘 픽업/배달 완료
    cur.execute(f"""
        SELECT {select_fields}
        FROM invoicebase ib
        {join_tables}
        WHERE ib.isdeleted = false
        AND e.id IS NULL
        AND (
            (ib.pickupdate IS NOT NULL AND ib.pickupdate::text != '' AND DATE(ib.pickupdate) = %s)
            OR 
            (ib.documentlocation_id IN (1153, 3221) AND DATE(ib.locationchangedate) = %s)
        )
        ORDER BY ib.invoicenumber DESC
    """, (target_date, target_date))
    picked_up = cur.fetchall()

    # 5. 오늘 결제한 잡 (Post된 인보이스 기준)
    cur.execute(f"""
        SELECT DISTINCT 
            tsr.invoicenumber, 
            ib.name as job_name, 
            ib.ordereddate,
            ib.wanteddate,
            tsr.total as grandtotal,
            TRIM(CONCAT(p_con.firstname, ' ', p_con.lastname)) as contact_name,
            TRIM(a.title) as account_name
        FROM tapesalerecord tsr
        JOIN invoicebase ib ON tsr.invoicenumber = ib.invoicenumber
        LEFT JOIN estimate e ON ib.id = e.id
        LEFT JOIN contact c ON ib.contact_id = c.id
        LEFT JOIN party p_con ON c.id = p_con.id
        LEFT JOIN account a ON ib.account_id = a.id
        WHERE ib.isdeleted = false
        AND tsr.isdeleted = false
        AND e.id IS NULL
        AND tsr.paymode != 'Charge'
        AND DATE(ib.offpendingdate) = %s
        ORDER BY tsr.invoicenumber DESC
    """, (target_date,))
    paid = cur.fetchall()

    cur.close()
    conn.close()

    def process_rows(rows):
        res = []
        for r in rows:
            if str(r.get('invoicenumber')) in hidden_list:
                continue
            d = dict(r)
            acc = (d.get("account_name") or "").strip()
            con = (d.get("contact_name") or "").strip()
            
            d["account_display"] = acc if acc else con
            d["contact_display"] = con if acc else ""
            res.append(d)
        return res

    return {
        "date": str(target_date),
        "new_today": process_rows(new_today),
        "in_progress": process_rows(in_progress),
        "ready": process_rows(ready),
        "picked_up": process_rows(picked_up),
        "paid": process_rows(paid)
    }
