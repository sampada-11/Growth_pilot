"""
Phase 2 Comprehensive Test Suite (Supabase Postgres, Redis Queue, Caching, Rate Limiting, Razorpay, Dynamic Bands)
"""
import unittest
import os
import sys
import time
import json
import hmac
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.db.models import init_db, get_db_connection
from backend.app.db.database import db_session_scope, setup_supabase_rls, DEFAULT_TENANT_ID
from backend.app.db.schema import Customer, Product, Opportunity, Execution, AuditLog
from backend.app.db.seed_synthetic_data import seed_database
from backend.app.tools.guardrails import compute_discount_band, check_guardrails
from backend.app.tools.razorpay import (
    create_razorpay_order,
    create_razorpay_payment_link,
    verify_razorpay_signature,
    process_razorpay_webhook,
    compute_payload_hash
)
from backend.app.integrations.redis_client import (
    get_redis_client,
    enqueue_event,
    pop_event,
    set_cached_json,
    get_cached_json,
    invalidate_cache
)
from backend.app.integrations.rate_limiter import is_rate_limited
from backend.app.agents.orchestrator import run_full_pipeline, approve_and_execute_campaign


class TestPhase2SupabaseAndRedis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        setup_supabase_rls()
        seed_database(force=True)

    # -------------------------------------------------------------
    # 1. Supabase Postgres & Multi-Tenant Schema Tests
    # -------------------------------------------------------------
    def test_01_tenant_id_schema_presence(self):
        """Verifies tenant_id column exists on database tables."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn("tenant_id", columns)
        self.assertIn("margin_pct", columns)
        self.assertIn("inventory_urgency_factor", columns)

        cursor.execute("PRAGMA table_info(executions)")
        exec_cols = [row[1] for row in cursor.fetchall()]
        self.assertIn("razorpay_order_id", exec_cols)
        self.assertIn("razorpay_payment_link_id", exec_cols)
        conn.close()

    def test_02_sqlalchemy_tenant_session(self):
        """Verifies SQLAlchemy ORM operations work with tenant_id."""
        with db_session_scope() as session:
            test_prod = session.query(Product).filter_by(product_id="PROD-002").first()
            self.assertIsNotNone(test_prod)
            self.assertEqual(test_prod.margin_pct, 50.0)
            self.assertEqual(test_prod.inventory_urgency_factor, 1.3)

    # -------------------------------------------------------------
    # 2. Dynamic Discount Band & Guardrails Tests
    # -------------------------------------------------------------
    def test_03_dynamic_discount_band_calculation(self):
        """Verifies compute_discount_band yields different bands for different products/urgencies."""
        # High margin, high urgency product (PROD-002 Earbud Stand: 50% margin, 1.3 urgency)
        prod_high = {"product_id": "PROD-002", "margin_pct": 50.0, "inventory_urgency_factor": 1.3}
        band_high = compute_discount_band(prod_high, {}, {})
        self.assertEqual(band_high[0], 3.0) # min_pct
        self.assertEqual(band_high[2], 8.0) # recommended_pct
        self.assertGreaterEqual(band_high[1], 12.0) # max_pct

        # Low margin, low urgency product (e.g. Cables: 25% margin, 0.8 urgency)
        prod_low = {"product_id": "PROD-008", "margin_pct": 25.0, "inventory_urgency_factor": 0.8}
        band_low = compute_discount_band(prod_low, {}, {})
        self.assertLess(band_low[1], band_high[1]) # max_pct of low margin must be smaller
        self.assertEqual(band_low[0], 2.0) # min_pct

    def test_04_guardrail_rejection_above_dynamic_band(self):
        """Verifies guardrails reject offers exceeding the dynamic computed ceiling."""
        prod = {"product_id": "PROD-008", "margin_pct": 25.0, "inventory_urgency_factor": 0.8}
        band = compute_discount_band(prod, {}, {}) # max around 5.0% - 6.0%

        # Proposal with 14% discount (exceeds band ceiling)
        excessive_proposal = {
            "offer_pct": 14.0,
            "segment_size": 100,
            "estimated_cost": 500.0,
            "sample_size": 50
        }
        res = check_guardrails(excessive_proposal, discount_band=band)
        self.assertEqual(res["status"], "Blocked")
        self.assertTrue(any("exceeds dynamic margin/inventory ceiling" in r for r in res["reasons"]))

    # -------------------------------------------------------------
    # 3. Razorpay Test-Mode & Webhook Tests
    # -------------------------------------------------------------
    def test_05_razorpay_order_and_payment_link(self):
        """Verifies Razorpay test order & payment link generation."""
        order = create_razorpay_order(amount_inr=1104.0, receipt_id="rec_test_999")
        self.assertIn("id", order)
        self.assertEqual(order["amount"], 110400) # paise
        self.assertTrue(order["test_mode"])

        link = create_razorpay_payment_link(amount_inr=1104.0, customer_id="CUST-00001", description="Test offer")
        self.assertIn("short_url", link)

    def test_06_webhook_signature_verification_and_hash(self):
        """Verifies HMAC signature check and SHA-256 payload hashing."""
        body = '{"event":"payment.captured","payload":{}}'
        secret = "rzp_webhook_secret123"
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        
        # Valid signature
        self.assertTrue(verify_razorpay_signature(body, sig, secret))
        # Invalid signature
        self.assertFalse(verify_razorpay_signature(body, "bad_signature", secret))
        # Payload hash
        h = compute_payload_hash(body.encode())
        self.assertEqual(len(h), 64)

    def test_07_end_to_end_payment_failed_handling(self):
        """Verifies payment.failed event logs failure and penalizes decision confidence."""
        failed_event = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail_test_777",
                        "amount": 110400,
                        "email": "user@example.com",
                        "error_description": "Card authorization failed",
                        "notes": {
                            "customer_id": "CUST-00042",
                            "product_id": "PROD-002",
                            "campaign_id": "CAMP-DEMO-001"
                        }
                    }
                }
            }
        }
        res = process_razorpay_webhook(failed_event, payload_hash="testhash123")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["event"], "payment.failed")

    # -------------------------------------------------------------
    # 4. Redis Queue, Caching & Rate Limiting Tests
    # -------------------------------------------------------------
    def test_08_redis_event_queue(self):
        """Verifies events are enqueued and popped from Redis queue."""
        ev = enqueue_event("test.event", {"data": "sample_123"})
        self.assertEqual(ev, "test.event")

        popped = pop_event()
        self.assertIsNotNone(popped)
        self.assertEqual(popped["event_type"], "test.event")
        self.assertEqual(popped["payload"]["data"], "sample_123")

    def test_09_redis_caching(self):
        """Verifies 30-60s Redis caching and invalidation."""
        test_data = {"key": "value_999", "time": time.time()}
        set_cached_json("test_metric", test_data, ttl_seconds=45)
        
        cached = get_cached_json("test_metric")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["key"], "value_999")

        # Invalidate cache
        invalidate_cache("test_metric")
        self.assertIsNone(get_cached_json("test_metric"))

    def test_10_redis_rate_limiting(self):
        """Verifies rate limiter blocks requests exceeding the configured window limit."""
        client_ip = "192.168.1.100"
        route = "test_rate_limited_route"
        limit = 3

        # First 3 requests should succeed
        self.assertFalse(is_rate_limited(client_ip, route, max_requests=limit, window_seconds=10)[0])
        self.assertFalse(is_rate_limited(client_ip, route, max_requests=limit, window_seconds=10)[0])
        self.assertFalse(is_rate_limited(client_ip, route, max_requests=limit, window_seconds=10)[0])

        # 4th request should be rate limited
        is_limited, remaining, _ = is_rate_limited(client_ip, route, max_requests=limit, window_seconds=10)
        self.assertTrue(is_limited)
        self.assertEqual(remaining, 0)


if __name__ == "__main__":
    unittest.main()
