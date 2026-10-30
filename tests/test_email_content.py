import asyncio
import unittest
from copy import deepcopy
from datetime import datetime
from email.utils import parseaddr
from unittest.mock import AsyncMock, patch

from app.services.email_service import generate_mobile_html, generate_plain_text, send_report_email


class ManagementEmailTest(unittest.TestCase):
    def test_management_email_keeps_details_and_partial_balance_in_both_formats(self):
        data = {
            "date": "2026-09-30",
            "paid": [{"invoicenumber": "60001", "account_display": "A & B", "job_name": "Half Pager",
                      "grandtotal": 7176.16, "ordereddate": "2026-09-28", "transaction_type": "PAID", "pay_method_display": "Credit Card",
                      "is_partial": True, "current_balance": 6822.41}],
            "new_today": [{"invoicenumber": "57400", "account_display": "New Client",
                           "job_name": "Poster", "grandtotal": 100, "ordereddate": "2026-09-30", "wanteddate": "2026-10-01"}],
            "in_progress": [{"invoicenumber": "57300", "account_display": "Print Co",
                             "job_name": "Signs", "grandtotal": 200, "status": "Printing", "ordereddate": "2026-09-29",
                             "hold_name": "Credit Hold"}],
            "ready": [{"invoicenumber": "57200", "account_display": None,
                       "job_name": "Banner", "grandtotal": 300}],
            "picked_up": [{"invoicenumber": "57100", "account_display": "Done Co",
                           "job_name": "Cards", "grandtotal": 400}],
        }
        spending = [{"vendor": "Paper Shop", "description": "Stock", "amount": 25.50}]

        with patch("app.services.email_service.spending_service.get_spending_by_date", return_value=spending) as get_spending, \
             patch("app.services.email_service.settings_service.load_settings", return_value={
                 "boss_emails": ["manager@example.com", "owner@example.com"], "report_title_prefix": "Shop"
             }), \
             patch("app.services.email_service.SMTP_CONFIG", {
                 "user": "reports@example.com", "host": "smtp.example.com", "port": 587,
                 "password": "test-password"
             }), \
             patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as smtp_send:
            asyncio.run(send_report_email(data))

        message = smtp_send.await_args.args[0]
        self.assertEqual(message["Subject"], "Overnight - 09/30/2026 Daily Report")
        self.assertEqual(parseaddr(str(message["From"])), ("Overnight Printing Seattle", "reports@example.com"))
        self.assertEqual(message["To"], "manager@example.com, owner@example.com")
        self.assertEqual(smtp_send.await_args.kwargs["username"], "reports@example.com")
        plain = message.get_body(("plain",)).get_content()
        html = message.get_body(("html",)).get_content()
        logo = next(part for part in message.walk() if part.get_content_type() == "image/png")
        self.assertEqual(logo["Content-ID"], "<overnight-logo>")
        self.assertTrue(logo.get_content().startswith(b"\x89PNG"))
        self.assertIn('src="cid:overnight-logo"', html)
        for text in (plain, html):
            self.assertIn("Shop Daily Report", text)
            for expected in ("$7,176.16", "$25.50", "60001", "57400", "57300", "57200", "57100",
                             "BAL DUE: $6,822.41", "New orders", "Ready for Pickup", "09/30/2026",
                             "Collected today", "Recorded spending"):
                self.assertIn(expected, text)
            for number in ("60001", "57400", "57300", "57200", "57100"):
                self.assertNotIn("#" + number, text)
            self.assertNotIn("Ordered: 09/30/2026", text)
            self.assertNotIn("Due:", text)
            self.assertNotIn("Ordered: 09/28/2026", text)
            self.assertNotIn("From visible report invoices", text)
            self.assertIn("Ordered: 09/29/2026", text)
            self.assertIn("Credit Hold · Status: Printing", text)
            for removed in ("Needs attention", "Production due dates", "Overdue"):
                self.assertNotIn(removed, text)
        self.assertIn("A &amp; B", html)
        for text in (html, plain):
            self.assertNotIn("last 7 days", text)
            self.assertNotIn("Jobs:", text)
        self.assertIn(">57200</div>", html)
        self.assertIn("57200 — Banner — $300.00", plain)
        self.assertIn("$100.00 order value", html)
        self.assertIn("New orders: 1 ($100.00 order value)", plain)
        self.assertIn("Recorded spending: $25.50", plain)
        headings = ["New Today", "In Progress", "Ready for Pickup", "Completed Today", "Paid Today", "Daily Spending"]
        self.assertEqual([html.index(f'>{heading} <span') for heading in headings],
                         sorted(html.index(f'>{heading} <span') for heading in headings))
        self.assertLess(html.index("Collected"), html.index("Paid Today"))
        get_spending.assert_called_once_with("2026-09-30")
        smtp_send.assert_awaited_once()

    def test_email_summary_uses_paid_rows_and_escapes_without_mutation(self):
        def job(number, due):
            return {"invoicenumber": number, "wanteddate": due, "account_display": 'A & <B>',
                    "job_name": '<script>alert("x")</script>', "grandtotal": 10, "status": "Printing"}

        data = {
            "date": "2026-10-27",
            "new_today": [job('1', '2026-10-26'), job('2', '2026-10-27T23:00:00-07:00'),
                          job('3', '2026-10-28'), job('4', None), job('5', '2026-10-26')],
            "in_progress": [job(1, '2026-10-26'), job('6', '2026-10-26'),
                            {**job('7', '2026-10-26'), "status": "Shipping"},
                            job('8', '2026-02-30'), job('9', datetime(2026, 10, 27, 15))],
            "ready": [job('5', None)], "picked_up": [job('6', None)],
            "paid": [{**job('1', None), "grandtotal": 12.5, "invoice_total": 999, "current_balance": 900}],
        }
        original = deepcopy(data)
        spending = [{"vendor": "Ink", "amount": 4}, {"vendor": "Paper", "amount": "6.25"}]
        html = generate_mobile_html(data, spending, 'Shop <Seattle>')
        plain = generate_plain_text(data, spending, 'Shop <Seattle>')
        self.assertEqual(data, original)
        for text in (html, plain):
            self.assertIn('$12.50', text)
            self.assertNotIn('$999.00', text)
            self.assertIn('10/27/2026', text)
            self.assertIn('$50.00 order value', text)
            self.assertIn('$10.25', text)
        self.assertIn('A &amp; &lt;B&gt;', html)
        self.assertIn('Shop &lt;Seattle&gt; Daily Report', html)
        self.assertNotIn('<script>', html)
        self.assertIn('Collected today: $12.50\n', plain)

    def test_empty_email_has_zero_summary_and_all_sections(self):
        data = {"date": "2026-10-30", **{key: [] for key in ('new_today', 'in_progress', 'ready', 'picked_up', 'paid')}}
        html = generate_mobile_html(data, [])
        plain = generate_plain_text(data, [])
        self.assertIn('$0.00', html)
        self.assertEqual(html.count('$0.00'), 3)
        self.assertEqual(html.count('<caption '), 6)
        self.assertEqual(plain.count('No items for this date.'), 6)
        self.assertIn('Recorded spending: $0.00', plain)
        self.assertNotIn('nan', html.lower())

if __name__ == "__main__":
    unittest.main()
