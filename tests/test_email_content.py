import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.services.email_service import send_report_email


class ManagementEmailTest(unittest.TestCase):
    def test_management_email_keeps_details_and_partial_balance_in_both_formats(self):
        data = {
            "date": "2026-09-30",
            "paid": [{"invoicenumber": "60001", "account_display": "A & B", "job_name": "Half Pager",
                      "grandtotal": 7176.16, "transaction_type": "PAID", "pay_method_display": "Credit Card",
                      "is_partial": True, "current_balance": 6822.41}],
            "new_today": [{"invoicenumber": "57400", "account_display": "New Client",
                           "job_name": "Poster", "grandtotal": 100}],
            "in_progress": [{"invoicenumber": "57300", "account_display": "Print Co",
                             "job_name": "Signs", "grandtotal": 200, "status": "Printing"}],
            "ready": [{"invoicenumber": "57200", "account_display": "Ready Co",
                       "job_name": "Banner", "grandtotal": 300}],
            "picked_up": [{"invoicenumber": "57100", "account_display": "Done Co",
                           "job_name": "Cards", "grandtotal": 400}],
        }
        spending = [{"vendor": "Paper Shop", "description": "Stock", "amount": 25.50}]

        with patch("app.services.email_service.spending_service.get_spending_by_date", return_value=spending) as get_spending, \
             patch("app.services.email_service.settings_service.load_settings", return_value={
                 "boss_emails": ["manager@example.com"], "report_title_prefix": "Shop"
             }), \
             patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as smtp_send:
            asyncio.run(send_report_email(data))

        message = smtp_send.await_args.args[0]
        self.assertEqual(message["Subject"], "Shop 2026-09-30 Daily Report")
        plain, html = (part.get_content() for part in message.iter_parts())
        for text in (plain, html):
            for expected in ("$7,176.16", "$25.50", "#60001", "#57300", "#57200", "#57100",
                             "BAL DUE: $6,822.41", "New Orders Today", "Ready for Pickup"):
                self.assertIn(expected, text)
            self.assertNotIn("#57400", text)
        self.assertIn("A &amp; B", html)
        self.assertIn("Order Value: $100.00", html)
        self.assertLess(html.index("TOTAL COLLECTED TODAY"), html.index("Payments Today"))
        get_spending.assert_called_once_with("2026-09-30")
        smtp_send.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
