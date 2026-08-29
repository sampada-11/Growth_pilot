"""
Unit Tests for Razorpay Test-Mode & Webhook Integration
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.db.models import init_db
from backend.app.tools.razorpay import (
    create_razorpay_order,
    create_razorpay_payment_link,
    verify_razorpay_signature,
    process_razorpay_webhook
)


class TestRazorpayIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_create_razorpay_order(self):
        """Tests Razorpay test-mode order creation."""
        order = create_razorpay_order(amount_inr=1200.0, receipt_id="receipt_test_123")
        self.assertIn("id", order)
        self.assertEqual(order["amount"], 120000) # Amount in paise
        self.assertTrue(order["test_mode"])

    def test_02_create_payment_link(self):
        """Tests Razorpay payment link generation."""
        link = create_razorpay_payment_link(amount_inr=1104.0, customer_id="CUST-00001", description="Test offer")
        self.assertIn("short_url", link)
        self.assertTrue(link["short_url"].startswith("http"))

    def test_03_signature_verification(self):
        """Tests HMAC SHA256 signature verification logic."""
        body = '{"event":"payment.captured"}'
        secret = "test_secret_key"
        import hmac, hashlib
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        self.assertTrue(verify_razorpay_signature(body, sig, secret))
        self.assertFalse(verify_razorpay_signature(body, "invalid_sig", secret))

    def test_04_process_webhook_event(self):
        """Tests webhook processing for payment.failed and payment.captured events."""
        event_failed = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_failed123",
                        "amount": 120000,
                        "email": "test@example.com",
                        "error_description": "OTP failed",
                        "notes": {"customer_id": "CUST-00042", "product_id": "PROD-002"}
                    }
                }
            }
        }
        res_failed = process_razorpay_webhook(event_failed)
        self.assertEqual(res_failed["status"], "success")
        self.assertEqual(res_failed["event"], "payment.failed")

        event_success = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_cap123",
                        "amount": 120000,
                        "email": "test@example.com",
                        "notes": {"customer_id": "CUST-00042", "campaign_id": "CAMP-DEMO-001"}
                    }
                }
            }
        }
        res_success = process_razorpay_webhook(event_success)
        self.assertEqual(res_success["status"], "success")


if __name__ == "__main__":
    unittest.main()
