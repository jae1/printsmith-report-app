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

if __name__ == '__main__':
    unittest.main()
