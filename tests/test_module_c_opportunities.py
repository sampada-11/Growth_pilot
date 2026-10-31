"""
Module C: Growth Opportunities Lifecycle & State Machine Test Suite (§8.3, FR-023 to FR-031)
Verifies:
1. List endpoint returning opportunities ranked by priority with all Section 9.3 fields.
2. Filtering by lifecycle status and risk level.
3. Detail view with root cause hypotheses, analytics references, and transition history.
4. Strategy editing dynamically recomputing financial impact and priority score.
5. Guardrail re-check gating approvals (422 on BLOCK).
6. Server-enforced state machine (409 on invalid transition).
7. Role-based approval access (403 on insufficient role).
8. Rejection requiring mandatory reason.
9. Cross-tenant isolation.
"""
import unittest
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth.jwt_auth import create_access_token
from backend.app.db.models import init_db, get_db_connection
from backend.app.db.seed_synthetic_data import seed_database
from backend.app.agents.orchestrator import run_full_pipeline

TENANT_ALPHA = "tenant_store_alpha"
TENANT_BETA = "tenant_store_beta"


class TestModuleCOpportunities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database(force=False)
        cls.client = TestClient(app)

        # Authorized tokens
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
        cls.token_alpha_owner = create_access_token({
            "sub": "usr_alpha_owner",
            "tenant_id": TENANT_ALPHA,
            "role": "owner"
        })
        # Unauthorized token (viewer)
        cls.token_alpha_viewer = create_access_token({
            "sub": "usr_alpha_viewer",
            "tenant_id": TENANT_ALPHA,
            "role": "viewer"
        })
        # Tenant Beta token
        cls.token_beta = create_access_token({
            "sub": "usr_beta_mgr",
            "tenant_id": TENANT_BETA,
            "role": "growth_manager"
        })

    def setUp(self):
        # Ensure at least one fresh test opportunity exists for alpha
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO opportunities (
                opportunity_id, tenant_id, title, description, problem,
                root_cause, affected_customers, product_id, supporting_analytics,
                strategy, expected_impact, est_revenue_impact, est_profit_impact,
                confidence, urgency_factor, priority_score, priority_rank,
                risk_level, approval_status, execution_status, lifecycle_state,
                created_at, updated_at
            ) VALUES (
                'OPP-TEST-C01', 'tenant_store_alpha', 'Earbud Stand Cart Recovery',
                '71% Cart Abandonment on Earbud Stand', 'Cart Abandonment on PROD-002',
                '{"hypotheses": [{"text": "High shipping cost", "evidence_refs": ["funnel.abandonment"], "strength": "high"}]}',
                '{"count": 850, "segment_id": "SEG-001"}', 'PROD-002',
                '{"abandonment_rate": 71.0}',
                '{"type": "targeted_discount", "discount_pct": 8.0, "channels": ["email", "push"], "audience_size": 850}',
                81600.0, 81600.0, 29376.0,
                0.78, 1.25, 79560.0, 1,
                'low', 'pending', 'not_started', 'pending_approval',
                datetime('now'), datetime('now')
            )
        """)
        conn.commit()
        conn.close()

    def test_01_unauthenticated_request_rejected(self):
        """FR-023: Unauthenticated requests to /api/v1/opportunities must return 401."""
        res = self.client.get("/api/v1/opportunities")
        self.assertEqual(res.status_code, 401)

    def test_02_list_opportunities_ranked_by_priority(self):
        """FR-024, FR-025: List endpoint returns opportunities ranked by priority score with all Section 9.3 fields."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res = self.client.get("/api/v1/opportunities", headers=headers)
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

        # Verify sorted descending by priority_score
        scores = [item["priority"]["score"] for item in data]
        self.assertEqual(scores, sorted(scores, reverse=True))

        first = data[0]
        # Verify mandatory Section 9.3 fields
        self.assertIn("id", first)
        self.assertEqual(first["tenant_id"], TENANT_ALPHA)
        self.assertIn("problem", first)
        self.assertIn("root_cause", first)
        self.assertIn("affected_customers", first)
        self.assertIn("supporting_analytics", first)
        self.assertIn("strategy", first)
        self.assertIn("est_revenue_impact", first)
        self.assertIn("est_profit_impact", first)
        self.assertIn("confidence", first)
        self.assertIn("priority", first)
        self.assertIn("risk_level", first)
        self.assertIn("lifecycle_state", first)
        self.assertIn("guardrail", first)
        self.assertEqual(first["is_simulated"], False)

    def test_03_filter_opportunities_by_status_and_risk(self):
        """FR-025: List endpoint filterable by status/lifecycle_state and risk_level."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res = self.client.get("/api/v1/opportunities?status=pending_approval&risk=low", headers=headers)
        self.assertEqual(res.status_code, 200)
        items = res.json()
        for item in items:
            self.assertIn(item["lifecycle_state"], ["pending_approval", "open"])
            self.assertEqual(item["risk_level"], "low")

    def test_04_opportunity_detail_view_and_history(self):
        """FR-026: Detail view shows problem, root cause hypotheses, analytics, strategy, impact, guardrail, and history."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res = self.client.get("/api/v1/opportunities/OPP-TEST-C01", headers=headers)
        self.assertEqual(res.status_code, 200)
        detail = res.json()

        self.assertEqual(detail["id"], "OPP-TEST-C01")
        self.assertEqual(detail["product_id"], "PROD-002")
        self.assertIn("hypotheses", detail["root_cause"])
        self.assertEqual(detail["root_cause"]["hypotheses"][0]["strength"], "high")
        self.assertIn("history", detail)
        self.assertIsInstance(detail["history"], list)

    def test_05_edit_strategy_recomputes_impact_and_reruns_guardrails(self):
        """FR-027: Editing strategy recomputes financial impact and re-runs Guardrail Agent."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        update_payload = {
            "discount_pct": 10.0,
            "audience_size": 900,
            "channel": "email"
        }
        res = self.client.patch("/api/v1/opportunities/OPP-TEST-C01/strategy", json=update_payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        updated = res.json()

        # Check strategy updated
        self.assertEqual(updated["strategy"]["discount_pct"], 10.0)
        self.assertEqual(updated["strategy"]["audience_size"], 900)

        # Check deterministic formula recomputed:
        # Audience = 900, Delta Conversion = (14 - 6)% = 0.08, Base Price = 1200
        # Expected Revenue Impact = 900 * 0.08 * 1200 = 86,400
        expected_rev = 86400.0
        self.assertEqual(updated["est_revenue_impact"]["value"], expected_rev)

        # Check priority score recomputed: 86,400 * 0.78 * 1.25 = 84,240
        self.assertEqual(updated["priority"]["score"], 84240.0)

        # Guardrail re-run check
        self.assertIn("guardrail", updated)
        self.assertIn(updated["guardrail"]["decision"], ["ALLOW", "REQUIRE_APPROVAL"])

        # Verify event was recorded in history
        self.assertGreaterEqual(len(updated["history"]), 1)
        last_event = updated["history"][-1]
        self.assertIn("Strategy modified", last_event["reason"])

    def test_06_approve_opportunity_role_check_and_state_machine(self):
        """FR-028, FR-029: Role check and state machine governance for approval."""
        # 1. Viewer role attempt -> 403 INSUFFICIENT_ROLE
        res_viewer = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/approve",
            json={"note": "Viewer attempt"},
            headers={"Authorization": f"Bearer {self.token_alpha_viewer}"}
        )
        self.assertEqual(res_viewer.status_code, 403)
        self.assertEqual(res_viewer.json()["detail"]["error"]["code"], "INSUFFICIENT_ROLE")

        # 2. Authorized role (growth_manager) -> 200 Approved
        res_mgr = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/approve",
            json={"note": "Approved for execution"},
            headers={"Authorization": f"Bearer {self.token_alpha_manager}"}
        )
        self.assertEqual(res_mgr.status_code, 200)
        appr_data = res_mgr.json()
        self.assertEqual(appr_data["lifecycle_state"], "approved")
        self.assertEqual(appr_data["approved_by"], "usr_alpha_mgr")
        self.assertEqual(appr_data["guardrail_recheck"], "ALLOW")

        # 3. Attempting to approve an already approved opportunity -> 409 INVALID_TRANSITION
        res_conflict = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/approve",
            json={"note": "Duplicate approval"},
            headers={"Authorization": f"Bearer {self.token_alpha_manager}"}
        )
        self.assertEqual(res_conflict.status_code, 409)
        self.assertEqual(res_conflict.json()["detail"]["error"]["code"], "INVALID_TRANSITION")

    def test_07_reject_opportunity_requires_reason_and_updates_state(self):
        """FR-027, FR-028: Rejection requires mandatory reason and transitions state to rejected."""
        # 1. Empty reason -> 422 MISSING_REASON
        res_empty = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/reject",
            json={"reason": "   "},
            headers={"Authorization": f"Bearer {self.token_alpha_manager}"}
        )
        self.assertEqual(res_empty.status_code, 422)

        # 2. Valid reason -> 200 Rejected
        res_reject = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/reject",
            json={"reason": "Margin degradation concerns on this product"},
            headers={"Authorization": f"Bearer {self.token_alpha_manager}"}
        )
        self.assertEqual(res_reject.status_code, 200)
        rej_data = res_reject.json()
        self.assertEqual(rej_data["lifecycle_state"], "rejected")
        self.assertEqual(rej_data["rejection_reason"], "Margin degradation concerns on this product")

        # 3. Illegal transition from rejected to approved -> 409 INVALID_TRANSITION
        res_illegal = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/approve",
            json={"note": "Cannot revive rejected"},
            headers={"Authorization": f"Bearer {self.token_alpha_manager}"}
        )
        self.assertEqual(res_illegal.status_code, 409)
        self.assertEqual(res_illegal.json()["detail"]["error"]["code"], "INVALID_TRANSITION")

    def test_08_guardrail_block_prevents_approval(self):
        """FR-019, FR-027: If strategy violates guardrails (e.g. 35% discount > 20% limit), approval is blocked (422)."""
        # Set aggressive discount that triggers GR-01 BLOCK
        res_patch = self.client.patch(
            "/api/v1/opportunities/OPP-TEST-C01/strategy",
            json={"discount_pct": 35.0},
            headers={"Authorization": f"Bearer {self.token_alpha_manager}"}
        )
        self.assertEqual(res_patch.status_code, 200)
        self.assertEqual(res_patch.json()["guardrail"]["decision"], "BLOCK")

        # Attempting to approve must fail with 422 GUARDRAIL_BLOCKED
        res_appr = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/approve",
            json={"note": "Bypassing guardrail"},
            headers={"Authorization": f"Bearer {self.token_alpha_admin}"}
        )
        self.assertEqual(res_appr.status_code, 422)
        err = res_appr.json()["detail"]["error"]
        self.assertEqual(err["code"], "GUARDRAIL_BLOCKED")
        self.assertGreaterEqual(len(err["rules"]), 1)

    def test_09_cross_tenant_isolation_in_opportunities(self):
        """D-14, FR-023: Tenant Beta cannot access or mutate Tenant Alpha's opportunities."""
        headers_beta = {"Authorization": f"Bearer {self.token_beta}"}

        # 1. Detail view cross-tenant attempt
        res_get = self.client.get("/api/v1/opportunities/OPP-TEST-C01", headers=headers_beta)
        self.assertEqual(res_get.status_code, 404)

        # 2. Strategy patch cross-tenant attempt
        res_patch = self.client.patch(
            "/api/v1/opportunities/OPP-TEST-C01/strategy",
            json={"discount_pct": 5.0},
            headers=headers_beta
        )
        self.assertEqual(res_patch.status_code, 404)

        # 3. Approval cross-tenant attempt
        res_appr = self.client.post(
            "/api/v1/opportunities/OPP-TEST-C01/approve",
            json={"note": "Hacking tenant A"},
            headers=headers_beta
        )
        self.assertEqual(res_appr.status_code, 404)

    def test_10_normalized_priority_scoring_formula(self):
        """Verifies Priority = 0.35I + 0.25C + 0.20F + 0.20E normalized multicriteria formula."""
        from backend.app.tools.scoring import score_opportunity
        # Earbud Charging Stand flagship scenario:
        # Expected lift: 81600.0, Confidence: 0.78, Urgency: 1.25, Feasibility: 90.0
        score_res = score_opportunity(
            insight={},
            expected_impact_revenue=81600.0,
            confidence=0.78,
            urgency_factor=1.25,
            feasibility=90.0
        )
        self.assertIn("normalized_priority", score_res)
        self.assertIn("impact_score", score_res)
        self.assertIn("confidence_score", score_res)
        self.assertIn("feasibility_score", score_res)
        self.assertIn("urgency_score", score_res)
        self.assertEqual(score_res["impact_score"], 81.6)
        self.assertEqual(score_res["confidence_score"], 78.0)
        self.assertEqual(score_res["feasibility_score"], 90.0)
        self.assertEqual(score_res["urgency_score"], 85.0)
        # 0.35*81.6 + 0.25*78.0 + 0.20*90.0 + 0.20*85.0 = 28.56 + 19.50 + 18.00 + 17.00 = 83.06 -> 83.1
        self.assertEqual(score_res["normalized_priority"], 83.1)
        self.assertEqual(score_res["formula"], "Priority = 0.35*I + 0.25*C + 0.20*F + 0.20*E")

    def test_11_recommendation_card_fields_and_lifecycle_stages(self):
        """Verifies that opportunity records contain all required card fields and follow 6-stage lifecycle."""
        headers = {"Authorization": f"Bearer {self.token_alpha_manager}"}
        res = self.client.get("/api/v1/opportunities", headers=headers)
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertGreaterEqual(len(items), 1)

        opp = items[0]
        # Required specification fields
        self.assertIn("opportunity", opp)
        self.assertIn("product", opp)
        self.assertIn("target_segment", opp)
        self.assertIn("affected_customers", opp)
        self.assertIn("root_cause", opp)
        self.assertIn("proposed_action", opp)
        self.assertIn("estimated_impact", opp)
        self.assertIn("risk", opp)
        self.assertIn("status", opp)

        # 6-stage lifecycle transition test: detected -> analysed -> approved -> executing -> completed -> evaluated
        opp_id = "OPP-LIFECYCLE-TEST"
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO opportunities (
                opportunity_id, tenant_id, problem, lifecycle_state, approval_status,
                est_revenue_impact, confidence, urgency_factor, priority_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (opp_id, TENANT_ALPHA, "Lifecycle Test Opp", "detected", "pending", 81600.0, 0.78, 1.25, 79560.0))
        conn.commit()
        conn.close()

        # Step 1: detected -> analysed
        r1 = self.client.post(f"/api/v1/opportunities/{opp_id}/transition", json={"to_state": "analysed"}, headers=headers)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["lifecycle_state"], "analysed")

        # Step 2: analysed -> approved
        r2 = self.client.post(f"/api/v1/opportunities/{opp_id}/approve", json={"note": "Approval test"}, headers=headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["lifecycle_state"], "approved")

        # Step 3: approved -> executing
        r3 = self.client.post(f"/api/v1/opportunities/{opp_id}/transition", json={"to_state": "executing"}, headers=headers)
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["lifecycle_state"], "executing")

        # Step 4: executing -> completed
        r4 = self.client.post(f"/api/v1/opportunities/{opp_id}/transition", json={"to_state": "completed"}, headers=headers)
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()["lifecycle_state"], "completed")

        # Step 5: completed -> evaluated
        r5 = self.client.post(f"/api/v1/opportunities/{opp_id}/transition", json={"to_state": "evaluated"}, headers=headers)
        self.assertEqual(r5.status_code, 200)
        self.assertEqual(r5.json()["lifecycle_state"], "evaluated")



if __name__ == "__main__":
    unittest.main()

