import unittest
from datetime import date
from app.services.report_service import get_report_data

class TestBatchPaymentFix(unittest.TestCase):
    def test_consolidated_ar_payment_attribution(self):
        # Target date where we know a batch payment occurred
        target_date = date(2026, 6, 16)
        data = get_report_data(target_date)
        
        # Specific invoices from the reported batch payment
        target_invs = {
            '56634': 92.20,
            '56631': 252.20,
            '56622': 570.87,
            '56615': 1438.24,
            '56607': 751.12,
            '56569': 1438.24
        }
        
        found_invs = {}
        for item in data['paid']:
            inv = item['invoicenumber']
            if inv in target_invs:
                found_invs[inv] = round(float(item['grandtotal']), 2)
        
        # Verify all target invoices were found and have correct amounts
        for inv, expected_amount in target_invs.items():
            with self.subTest(inv=inv):
                self.assertIn(inv, found_invs, f"Invoice #{inv} missing from Paid Today section")
                self.assertEqual(found_invs[inv], expected_amount, 
                                 f"Invoice #{inv} has incorrect amount. Expected {expected_amount}, got {found_invs[inv]}")

    def test_single_ar_partial_payment_uses_today_payment_not_invoice_total(self):
        data = get_report_data(date(2026, 6, 16))
        found = {
            item['invoicenumber']: round(float(item['grandtotal']), 2)
            for item in data['paid']
        }

        self.assertIn('56276', found)
        self.assertEqual(found['56276'], 20.62)

    def test_later_ar_batch_uses_remaining_balance_not_invoice_total(self):
        data = get_report_data(date(2026, 6, 22))
        found = {
            item['invoicenumber']: round(float(item['grandtotal']), 2)
            for item in data['paid']
        }

        self.assertIn('56276', found)
        self.assertEqual(found['56276'], 1668.52)

    def test_linked_plain_payment_splits_same_account_posting_batch(self):
        data = get_report_data(date(2026, 7, 15))
        found = {
            item['invoicenumber']: round(float(item['grandtotal']), 2)
            for item in data['paid']
        }

        self.assertIn('56762', found)
        self.assertIn('56896', found)
        self.assertEqual(found['56762'], 355.95)
        self.assertEqual(found['56896'], 199.99)
        self.assertEqual(round(found['56762'] + found['56896'], 2), 555.94)

    def test_previous_day_prepaid_invoice_is_not_paid_today(self):
        data = get_report_data(date(2026, 6, 18))
        paid_invoices = {item['invoicenumber'] for item in data['paid']}

        self.assertNotIn('56673', paid_invoices)

    def test_multi_method_plain_payments_cover_one_posting_batch(self):
        data = get_report_data(date(2026, 7, 24))
        found = {
            item['invoicenumber']: round(float(item['grandtotal']), 2)
            for item in data['paid']
        }
        expected = {
            '56858': 6658.69,
            '56954': 665.44,
            '56974': 4568.93,
        }

        for invoice_number, amount in expected.items():
            with self.subTest(invoice_number=invoice_number):
                self.assertIn(invoice_number, found)
                self.assertEqual(found[invoice_number], amount)
        self.assertEqual(
            round(sum(found[invoice_number] for invoice_number in expected), 2),
            11893.06,
        )

if __name__ == '__main__':
    unittest.main()
