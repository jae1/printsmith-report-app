content = open('main.py').read()

old = """    # 5. 오늘 결제한 잡
    cur.execute(\"\"\"
        SELECT DISTINCT ib.invoicenumber, ib.name, ib.grandtotal
        FROM tapesessionbatch tsb
        JOIN tapebatch_sessionbatches tbs ON tsb.id = tbs.sessionbatches_id
        JOIN tapebatch tb ON tbs.tapebatch_id = tb.id
        JOIN invoicebase ib ON tsb.account_id = ib.account_id
        LEFT JOIN estimate e ON ib.id = e.id
        WHERE DATE(tb.opendate) = %s
        AND tsb.isdeleted = false
        AND ib.isdeleted = false
        AND e.id IS NULL
        AND tsb.isposbatch = true
        ORDER BY ib.invoicenumber DESC
    \"\"\", (target_date,))
    paid = cur.fetchall()"""

new = """    # 5. 오늘 결제한 잡
    cur.execute(\"\"\"
        SELECT DISTINCT tsr.invoicenumber, ib.name, tsr.total as grandtotal
        FROM tapesalerecord tsr
        JOIN tapesessionbatch_transactions tst ON tsr.id = tst.transactions_id
        JOIN tapesessionbatch tsb ON tst.tapesessionbatch_id = tsb.id
        JOIN tapebatch_sessionbatches tbs ON tsb.id = tbs.sessionbatches_id
        JOIN tapebatch tb ON tbs.tapebatch_id = tb.id
        LEFT JOIN invoicebase ib ON tsr.invoicenumber = ib.invoicenumber
        LEFT JOIN estimate e ON ib.id = e.id
        WHERE DATE(tb.opendate) = %s
        AND tsr.isdeleted = false
        AND (e.id IS NULL OR ib.id IS NULL)
        ORDER BY tsr.invoicenumber DESC
    \"\"\", (target_date,))
    paid = cur.fetchall()"""

open('main.py', 'w').write(content.replace(old, new))
print("done")
