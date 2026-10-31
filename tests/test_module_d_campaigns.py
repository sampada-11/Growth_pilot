"""
Module D: Campaign Studio & Adapters Test Suite (§8.4, §9.4, FR-032 to FR-045)
Verifies:
1. Unauthenticated requests rejected (401).
2. Campaign creation from opportunity with live audience calculation (FR-032, FR-034).
3. AI content generation (3 email + 3 push) with deterministic character linter (FR-035).
4. Campaign preview resolving personalization tokens from sample customer (FR-036).
5. Role-based approval and guardrail gating (FR-029, FR-039).
6. Execution gating: unapproved campaign execution returns 409 NOT_APPROVED.
7. Execution gating: live mode without credentials returns 422 LIVE_ADAPTER_UNAVAILABLE (FR-042).
8. Demo mode execution with channel adapter, idempotent keys, and deliveries (FR-041, FR-043, FR-045).
9. Campaign performance reporting with computed KPIs and simulated labeling (FR-044).
10. Cross-tenant isolation.
"""
import unittest
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth.jwt_auth import create_access_token
from backend.app.db.models import init_db, get_db_connection
from backend.app.db.seed_synthetic_data import seed_database

TENANT_ALPHA = "tenant_store_alpha"
TENANT_BETA = "tenant_store_beta"


class TestModuleDCampaigns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database(force=False)
        cls.client = TestClient(app)

        cls.token_alpha_manager = create_access_token({
            "sub": "usr_alpha_mgr",
            "tenant_id": TENANT_ALPHA,
            "role": "growth_manager"
        })
        cls.token_alpha_admin = create_access_token({
            "sub": "usr_alpha_admin",
            "tenant_id": TENANT_ALPHA,
            "role": "admin"
        })
        cls.token_alpha_viewer = create_access_token({
            "sub": "usr_alpha_viewer",
            "tenant_id": TENANT_ALPHA,
            "role": "viewer"
        })
        cls.token_beta = create_access_token({
            "sub": "usr_beta_mgr",
            "tenant_id": TENANT_BETA,
            "role": "growth_manager"
        })

    def setUp(self):
        # Create a clean opportunity for testing campaign creation
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO opportunities (
                opportunity_id, tenant_id, title, description, problem,
                product_id, strategy, expected_impact, est_revenue_impact,
                est_profit_impact, confidence, urgency_factor, priority_score,
                priority_rank, risk_level, approval_status, execution_status,
                lifecycle_state, created_at, updated_at
            ) VALUES (
                'OPP-CAMP-001', 'tenant_store_alpha', 'Earbud Stand Recovery',
                '71% Cart Abandonment on Earbud Stand', 'Cart Abandonment on PROD-002',
                'PROD-002',
                '{"type": "targeted_discount", "discount_pct": 8.0, "channels": ["email", "push"], "audience_size": 850, "duration_days": 7, "budget_cap": 25000.0}',
                81600.0, 81600.0, 29376.0,
                0.78, 1.25, 79560.0,
                1, 'low', 'approved', 'not_started',
                'approved', datetime('now'), datetime('now')
            )
        """)
        conn.commit()
        conn.close()

    def test_01_unauthenticated_request_rejected(self):
        """FR-032: Unauthenticated requests to /api/v1/campaigns must return 401."""
        res_post = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts"})
        self.assertEqual(res_post.status_code, 401)

        res_get = self.client.get("/api/v1/campaigns")
        self.assertEqual(res_get.status_code, 401)

    def test_02_create_campaign_from_opportunity_and_audience_sizing(self):
        """FR-032, FR-034, FR-035: Creates campaign from opportunity, computes audience, and generates AI variants."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        payload = {
            "opportunity_id": "OPP-CAMP-001",
            "objective": "recover_abandoned_carts",
            "mode": "demo"
        }
        res = self.client.post("/api/v1/campaigns", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)

        camp = res.json()
        self.assertIn("campaign_id", camp)
        self.assertEqual(camp["tenant_id"], TENANT_ALPHA)
        self.assertEqual(camp["opportunity_id"], "OPP-CAMP-001")
        self.assertEqual(camp["objective"], "recover_abandoned_carts")
        self.assertEqual(camp["status"], "draft")
        self.assertEqual(camp["mode"], "demo")
        self.assertEqual(camp["is_simulated"], True)

        # Live audience size computed
        self.assertGreaterEqual(camp["audience_size"], 15)

        # Inherited discount
        self.assertEqual(camp["discount"]["value"], 8.0)
        self.assertEqual(camp["discount"]["product_id"], "PROD-002")

        # 3 email + 3 push variants generated (FR-035)
        variants = camp.get("content_variants", [])
        self.assertEqual(len(variants), 6)
        email_vars = [v for v in variants if v["channel"] == "email"]
        push_vars = [v for v in variants if v["channel"] == "push"]
        self.assertEqual(len(email_vars), 3)
        self.assertEqual(len(push_vars), 3)

    def test_03_content_linter_and_character_limits(self):
        """FR-035, GR-07: Content variants conform to character limits and pass deterministic linter."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts"}, headers=headers)
        self.assertEqual(res.status_code, 201)
        camp = res.json()

        for v in camp["content_variants"]:
            if v["channel"] == "email":
                # Subject ≤ 60 chars, preheader ≤ 100 chars
                self.assertLessEqual(len(v["subject"]), 60)
                if v.get("preheader"):
                    self.assertLessEqual(len(v["preheader"]), 100)
                self.assertIn("{{discount_pct}}", v["body"])
            elif v["channel"] == "push":
                # Title ≤ 50 chars, body ≤ 120 chars
                self.assertLessEqual(len(v["subject"]), 50) # stored as subject/title
                self.assertLessEqual(len(v["body"]), 120)

    def test_04_campaign_preview_with_personalization_tokens(self):
        """FR-036: Preview resolves tokens (first_name, product_name, discount_pct, checkout_url) on sample customer."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res_create = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts"}, headers=headers)
        camp_id = res_create.json()["campaign_id"]

        res_preview = self.client.get(f"/api/v1/campaigns/{camp_id}/preview", headers=headers)
        self.assertEqual(res_preview.status_code, 200)

        prev_data = res_preview.json()
        self.assertIn("sample_customer", prev_data)
        self.assertIn("previews", prev_data)

        # Check tokens resolved
        first_email = [p for p in prev_data["previews"] if p["channel"] == "email"][0]
        self.assertNotIn("{{first_name}}", first_email["body"])
        self.assertNotIn("{{discount_pct}}", first_email["body"])
        self.assertIn("8%", first_email["subject"])

    def test_05_approve_campaign_role_and_guardrail_gating(self):
        """FR-029, FR-039: Role check and guardrail gating on campaign approval."""
        headers_mgr = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        headers_viewer = {"Authorization": f"Bearer {self.token_alpha_viewer}"}

        res_create = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts"}, headers=headers_mgr)
        camp_id = res_create.json()["campaign_id"]

        # 1. Viewer attempt -> 403 INSUFFICIENT_ROLE
        res_viewer = self.client.post(f"/api/v1/campaigns/{camp_id}/approve", json={"note": "Viewer"}, headers=headers_viewer)
        self.assertEqual(res_viewer.status_code, 403)
        self.assertEqual(res_viewer.json()["detail"]["error"]["code"], "INSUFFICIENT_ROLE")

        # 2. Manager approval -> 200 Approved
        res_appr = self.client.post(f"/api/v1/campaigns/{camp_id}/approve", json={"note": "Approved"}, headers=headers_mgr)
        self.assertEqual(res_appr.status_code, 200)
        self.assertEqual(res_appr.json()["status"], "approved")

    def test_06_execute_unapproved_campaign_returns_409(self):
        """FR-028, FR-039: Attempting to execute an unapproved (draft) campaign returns 409 NOT_APPROVED."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res_create = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts"}, headers=headers)
        camp_id = res_create.json()["campaign_id"]

        res_exec = self.client.post(f"/api/v1/campaigns/{camp_id}/execute", json={"mode": "demo"}, headers=headers)
        self.assertEqual(res_exec.status_code, 409)
        self.assertEqual(res_exec.json()["detail"]["error"]["code"], "NOT_APPROVED")

    def test_07_execute_live_mode_without_credentials_returns_422(self):
        """FR-042: Executing in live mode when credentials are not configured returns 422 LIVE_ADAPTER_UNAVAILABLE."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res_create = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts", "mode": "live"}, headers=headers)
        camp_id = res_create.json()["campaign_id"]

        # Approve
        self.client.post(f"/api/v1/campaigns/{camp_id}/approve", json={"note": "Approved"}, headers=headers)

        # Attempt execute in live mode
        res_exec = self.client.post(f"/api/v1/campaigns/{camp_id}/execute", json={"mode": "live"}, headers=headers)
        self.assertEqual(res_exec.status_code, 422)
        self.assertEqual(res_exec.json()["detail"]["error"]["code"], "LIVE_ADAPTER_UNAVAILABLE")

    def test_08_execute_demo_mode_idempotency_and_deliveries(self):
        """FR-041, FR-043, FR-045: Demo mode execution dispatches via SimulatedAdapter with idempotent keys."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res_create = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts", "mode": "demo"}, headers=headers)
        camp_id = res_create.json()["campaign_id"]

        # Approve campaign
        self.client.post(f"/api/v1/campaigns/{camp_id}/approve", json={"note": "Approved"}, headers=headers)

        # Execute campaign
        res_exec = self.client.post(f"/api/v1/campaigns/{camp_id}/execute", json={"mode": "demo"}, headers=headers)
        self.assertEqual(res_exec.status_code, 202)
        exec_data = res_exec.json()
        self.assertEqual(exec_data["campaign_id"], camp_id)
        self.assertEqual(exec_data["mode"], "demo")
        self.assertEqual(exec_data["is_simulated"], True)
        self.assertGreater(exec_data["queued"], 0)

        # Check deliveries list endpoint
        res_deliv = self.client.get(f"/api/v1/campaigns/{camp_id}/deliveries", headers=headers)
        self.assertEqual(res_deliv.status_code, 200)
        deliv_data = res_deliv.json()
        self.assertGreater(deliv_data["total_deliveries"], 0)
        first_deliv = deliv_data["deliveries"][0]
        self.assertIn("status", first_deliv)
        self.assertIn("provider_message_id", first_deliv)
        self.assertEqual(first_deliv["is_simulated"], 1)

        # Retry execution: verify idempotency ensures 0 duplicate messages sent
        res_retry = self.client.post(f"/api/v1/campaigns/{camp_id}/execute", json={"mode": "demo"}, headers=headers)
        self.assertEqual(res_retry.status_code, 202)
        self.assertEqual(res_retry.json()["queued"], 0) # 0 new messages sent

    def test_09_campaign_performance_metrics_and_simulated_label(self):
        """FR-044: Performance endpoint aggregates metrics and badges simulated output."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res_create = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts"}, headers=headers)
        camp_id = res_create.json()["campaign_id"]
        self.client.post(f"/api/v1/campaigns/{camp_id}/approve", headers=headers)
        self.client.post(f"/api/v1/campaigns/{camp_id}/execute", json={"mode": "demo"}, headers=headers)

        res_perf = self.client.get(f"/api/v1/campaigns/{camp_id}/performance", headers=headers)
        self.assertEqual(res_perf.status_code, 200)
        perf = res_perf.json()

        self.assertEqual(perf["is_simulated"], True)
        metrics = perf["metrics"]
        self.assertIn("total_sends", metrics)
        self.assertIn("delivery_rate_pct", metrics)
        self.assertIn("open_rate_pct", metrics)
        self.assertIn("click_rate_pct", metrics)
        self.assertIn("conversions", metrics)
        self.assertIn("revenue_inr", metrics)
        self.assertIn("profit_inr", metrics)

    def test_10_cross_tenant_isolation_in_campaigns(self):
        """D-14: Tenant Beta cannot access Tenant Alpha's campaigns."""
        headers_alpha = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        headers_beta = {"Authorization": f"Bearer {self.token_beta}"}

        res_create = self.client.post("/api/v1/campaigns", json={"objective": "recover_abandoned_carts"}, headers=headers_alpha)
        camp_id = res_create.json()["campaign_id"]

        # Tenant Beta GET campaign detail -> 404
        res_get = self.client.get(f"/api/v1/campaigns/{camp_id}", headers=headers_beta)
        self.assertEqual(res_get.status_code, 404)

        # Tenant Beta approve attempt -> 404
        res_appr = self.client.post(f"/api/v1/campaigns/{camp_id}/approve", headers=headers_beta)
        self.assertEqual(res_appr.status_code, 404)

        # Tenant Beta execute attempt -> 404
        res_exec = self.client.post(f"/api/v1/campaigns/{camp_id}/execute", json={"mode": "demo"}, headers=headers_beta)
        self.assertEqual(res_exec.status_code, 404)

    def test_11_campaign_studio_objectives_and_content_regeneration(self):
        """Feature 1-3: Verify multiple objectives audience sizing, content regeneration, and filtering."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}

        # 1. Test audience sizing across different objectives
        for obj in ["reactivate_inactive", "retain_high_value", "promote_product", "bundle_upsell"]:
            res_create = self.client.post("/api/v1/campaigns", json={
                "name": f"Test {obj}",
                "objective": obj,
                "mode": "demo"
            }, headers=headers)
            self.assertEqual(res_create.status_code, 201)
            camp_data = res_create.json()
            self.assertEqual(camp_data["objective"], obj)
            self.assertGreater(camp_data["audience_size"], 0)
            self.assertEqual(len(camp_data["content_variants"]), 6)

        # 2. Test content regeneration endpoint with custom discount and product
        res_regen = self.client.post(f"/api/v1/campaigns/{camp_data['campaign_id']}/generate-content", json={
            "product_id": "PROD-001",
            "discount_pct": 12.0
        }, headers=headers)
        self.assertEqual(res_regen.status_code, 200)
        variants = res_regen.json()
        self.assertEqual(len(variants), 6)
        email_a = [v for v in variants if v["channel"] == "email" and v["variant"] == "variant_a"][0]
        self.assertIn("12%", email_a["subject"])

        # 3. Test listing campaigns filtered by objective and status
        res_list = self.client.get("/api/v1/campaigns?objective=bundle_upsell&status=draft", headers=headers)
        self.assertEqual(res_list.status_code, 200)
        camps = res_list.json()
        self.assertGreaterEqual(len(camps), 1)
        self.assertTrue(all(c["objective"] == "bundle_upsell" for c in camps))

    def test_12_channel_readiness_and_performance_roi(self):
        """Verifies channel readiness reporting (unsupported channels inactive) and ROI metric calculation."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res_ready = self.client.get("/api/v1/campaigns/channels/readiness", headers=headers)
        self.assertEqual(res_ready.status_code, 200)
        readiness = res_ready.json()
        self.assertIn("demo_mode", readiness)
        self.assertIn("live_mode", readiness)
        # SMS is explicitly unsupported
        self.assertFalse(readiness["demo_mode"]["sms"]["ready"])
        self.assertEqual(readiness["demo_mode"]["sms"]["status"], "unsupported")
        self.assertFalse(readiness["live_mode"]["sms"]["ready"])

        # Check ROI in performance endpoint
        # Create, approve and execute a test campaign to inspect performance
        res_create = self.client.post("/api/v1/campaigns", json={
            "name": "ROI Metric Test Campaign",
            "objective": "recover_abandoned_carts",
            "mode": "demo"
        }, headers=headers)
        camp_id = res_create.json()["campaign_id"]
        self.client.post(f"/api/v1/campaigns/{camp_id}/approve", json={"note": "Approved"}, headers=headers)
        self.client.post(f"/api/v1/campaigns/{camp_id}/execute", json={"mode": "demo"}, headers=headers)

        res_perf = self.client.get(f"/api/v1/campaigns/{camp_id}/performance", headers=headers)
        self.assertEqual(res_perf.status_code, 200)
        metrics = res_perf.json()["metrics"]
        self.assertIn("roi_pct", metrics)
        self.assertIn("total_sends", metrics)
        self.assertIn("delivery_rate_pct", metrics)
        self.assertIn("open_rate_pct", metrics)
        self.assertIn("click_rate_pct", metrics)
        self.assertIn("conversion_rate_pct", metrics)
        self.assertIn("revenue_inr", metrics)


if __name__ == "__main__":
    unittest.main()


