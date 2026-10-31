"""
Test Suite for Module E: Experiments Engine & Statistical Evaluation (§8.5, §9.5, FR-046 to FR-053).
Verifies:
1. Deterministic customer assignment (hash mod 10000, 20% holdout default).
2. Experiment creation from campaign & assignment persistence in experiment_assignments.
3. Rigorous statistical tests: two-proportion z-test, Welch's t-test, 95% confidence intervals.
4. SoundWave Audio validating scenario (6.0% control -> 14.0% treatment, +8.0% lift, ₹81,600 revenue lift, z > 2.5, p < 0.01).
5. Winner decision rule: treatment_wins, profitable_not_significant, control_wins, insufficient_data.
6. Minimum sample check (>=100 customers, >=5 conversions per arm) -> status 'insufficient_data'.
7. Learning signals recording in learning_signals and integration with GSA confidence prior.
8. Opportunity state transition from executing -> evaluated (FR-031).
9. Strict multi-tenant isolation on experiment resources.
"""
import unittest
import json
import uuid
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.jwt_auth import create_access_token
from backend.app.db.models import get_db_connection
from backend.app.experiments.service import ExperimentService
from backend.app.agents.strategy_agent import run_growth_strategy_agent


class TestModuleEExperiments(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Tenant A tokens (SoundWave Audio)
        cls.alpha_owner_token = create_access_token({
            "sub": "usr_alpha_owner",
            "user_id": "usr_alpha_owner",
            "email": "owner@soundwave.test",
            "role": "owner",
            "tenant_id": "tenant_store_alpha"
        })

        # Tenant B tokens (PulseWear)
        cls.beta_owner_token = create_access_token({
            "sub": "usr_beta_owner",
            "user_id": "usr_beta_owner",
            "email": "owner@pulsewear.test",
            "role": "owner",
            "tenant_id": "tenant_store_beta"
        })

    def _get_headers(self, token: str):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _create_and_execute_campaign(self, token: str, tenant_id: str, opp_id: str = None) -> str:
        """Helper to create, approve, and execute a campaign for experimentation."""
        # 1. Create campaign
        create_payload = {
            "opportunity_id": opp_id,
            "objective": "recover_abandoned_carts",
            "mode": "demo",
            "discount": {"type": "percentage", "percent": 8.0},
            "budget_total": 25000.0,
            "audience_size": 850
        }
        res = self.client.post("/api/v1/campaigns", headers=self._get_headers(token), json=create_payload)
        self.assertEqual(res.status_code, 201)
        camp_id = res.json()["campaign_id"]

        # 2. Approve campaign
        appr_res = self.client.post(f"/api/v1/campaigns/{camp_id}/approve", headers=self._get_headers(token), json={"note": "Approval for experiment"})
        self.assertEqual(appr_res.status_code, 200)

        # 3. Execute campaign
        exec_res = self.client.post(f"/api/v1/campaigns/{camp_id}/execute", headers=self._get_headers(token), json={"mode": "demo"})
        self.assertEqual(exec_res.status_code, 202)

        return camp_id

    def test_01_deterministic_customer_assignment(self):
        """FR-047: Customer assignment must be 100% deterministic and match holdout ratio."""
        tenant_id = "tenant_store_alpha"
        exp_id = "EXP-TEST-DETERMINISTIC"

        # Check repeatability on same customer
        arm1 = ExperimentService.deterministic_assignment(tenant_id, exp_id, "CUST-00042", holdout_pct=20.0)
        arm2 = ExperimentService.deterministic_assignment(tenant_id, exp_id, "CUST-00042", holdout_pct=20.0)
        self.assertEqual(arm1, arm2)

        # Check holdout ratio on 1,000 customers
        assignments = [
            ExperimentService.deterministic_assignment(tenant_id, exp_id, f"CUST-{i:05d}", holdout_pct=20.0)
            for i in range(1000)
        ]
        control_count = assignments.count("control")
        treatment_count = assignments.count("treatment")
        self.assertEqual(control_count + treatment_count, 1000)
        # Should be approximately 20% control (+/- 3%)
        self.assertTrue(170 <= control_count <= 230, f"Expected ~200 control out of 1000, got {control_count}")

    def test_02_create_experiment_and_assignment_persistence(self):
        """FR-046 & FR-047: Create experiment from campaign, persist assignments in DB."""
        camp_id = self._create_and_execute_campaign(self.alpha_owner_token, "tenant_store_alpha")

        exp_payload = {
            "campaign_id": camp_id,
            "holdout_pct": 20.0
        }
        res = self.client.post("/api/v1/experiments", headers=self._get_headers(self.alpha_owner_token), json=exp_payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()

        exp_id = data["experiment_id"]
        self.assertTrue(exp_id.startswith("EXP-"))
        self.assertEqual(data["campaign_id"], camp_id)
        self.assertEqual(data["holdout_pct"], 20.0)
        self.assertEqual(data["status"], "running")
        self.assertTrue(data["control_customers"] > 0)
        self.assertTrue(data["treatment_customers"] > 0)
        self.assertEqual(data["control_customers"] + data["treatment_customers"], 850)

        # Verify DB persistence of assignments
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM experiment_assignments WHERE experiment_id = ?", (exp_id,))
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 850)

    def test_03_evaluate_soundwave_demo_scenario(self):
        """FR-048 to FR-052: Statistical evaluation of SoundWave Audio validating scenario."""
        camp_id = self._create_and_execute_campaign(self.alpha_owner_token, "tenant_store_alpha")

        # Create experiment
        exp_res = self.client.post(
            "/api/v1/experiments",
            headers=self._get_headers(self.alpha_owner_token),
            json={"campaign_id": camp_id, "holdout_pct": 20.0}
        )
        exp_id = exp_res.json()["experiment_id"]

        # Evaluate experiment
        eval_res = self.client.post(
            f"/api/v1/experiments/{exp_id}/evaluate",
            headers=self._get_headers(self.alpha_owner_token),
            json={"end_experiment": True}
        )
        self.assertEqual(eval_res.status_code, 200)
        results = eval_res.json()

        # 1. Arm Metrics (FR-048)
        control = results["control"]
        treatment = results["treatment"]
        self.assertEqual(control["arm"], "control")
        self.assertEqual(treatment["arm"], "treatment")
        self.assertAlmostEqual(control["conversion_rate"], 0.06, delta=0.01)
        self.assertAlmostEqual(treatment["conversion_rate"], 0.14, delta=0.01)
        self.assertEqual(control["spend"], 0.0)
        self.assertTrue(treatment["spend"] > 0.0)

        # 2. Uplift Metrics (FR-049)
        uplift = results["uplift"]
        self.assertAlmostEqual(uplift["conversion_lift_abs"], 0.08, delta=0.01)
        self.assertEqual(uplift["incremental_revenue"], 81600.0)
        self.assertTrue(uplift["incremental_profit"] > 0)

        # 3. Two-Proportion Z-Test (FR-050)
        z_test = results["z_test"]
        self.assertTrue(z_test["z_score"] > 2.5)
        self.assertTrue(z_test["p_value"] < 0.01)
        self.assertTrue(z_test["significant"])
        # 95% CI lower bound must be strictly positive (excludes zero)
        self.assertTrue(z_test["ci_95"]["lower"] > 0.0)
        self.assertTrue(z_test["ci_95"]["upper"] > z_test["ci_95"]["lower"])

        # 4. Welch's T-Test (FR-050)
        t_test = results["welch_t_test"]
        self.assertTrue(t_test["t_stat"] > 2.0)
        self.assertTrue(t_test["p_value"] < 0.01)
        self.assertTrue(t_test["significant"])

        # 5. Winner Decision (FR-051)
        self.assertEqual(results["verdict"], "treatment_wins")
        self.assertEqual(results["status"], "completed")
        self.assertTrue(results["is_simulated"])
        self.assertIn("statistically significant conversion lift", results["verdict_reason"])

    def test_04_learning_signal_recorded_and_updates_gsa_prior(self):
        """FR-053: Completed experiments write learning_signals to update GSA confidence prior."""
        camp_id = self._create_and_execute_campaign(self.alpha_owner_token, "tenant_store_alpha")
        exp_res = self.client.post("/api/v1/experiments", headers=self._get_headers(self.alpha_owner_token), json={"campaign_id": camp_id})
        exp_id = exp_res.json()["experiment_id"]

        eval_res = self.client.post(f"/api/v1/experiments/{exp_id}/evaluate", headers=self._get_headers(self.alpha_owner_token), json={"end_experiment": True})
        self.assertEqual(eval_res.status_code, 200)

        # Verify learning signal in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM learning_signals WHERE source_experiment_id = ?", (exp_id,))
        sig = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(sig)
        self.assertEqual(sig[1], "tenant_store_alpha")
        self.assertAlmostEqual(sig[5], 0.08, delta=0.01)

        # Run Growth Strategy Agent to verify confidence prior boost
        opps = run_growth_strategy_agent(
            tenant_id="tenant_store_alpha",
            customer_data={},
            product_data={}
        )
        self.assertTrue(len(opps) > 0)
        # Opportunity confidence should reflect positive prior (>= 0.70)
        self.assertTrue(opps[0].confidence >= 0.70)

    def test_05_opportunity_state_transition_to_evaluated(self):
        """FR-031: Opportunity transitions to 'evaluated' when linked experiment completes."""
        # 1. Create opportunity in detected state
        conn = get_db_connection()
        cursor = conn.cursor()
        opp_id = f"OPP-EXP-TEST-{uuid.uuid4().hex[:6]}"
        cursor.execute("""
            INSERT INTO opportunities (
                opportunity_id, tenant_id, problem, lifecycle_state, approval_status,
                expected_impact, priority_score, product_id, created_at
            ) VALUES (?, ?, ?, 'detected', 'pending', 81600.0, 79560.0, 'PROD-002', '2026-10-30T10:00:00Z')
        """, (opp_id, "tenant_store_alpha", "Earbud stand cart abandonment"))
        conn.commit()
        conn.close()

        # Move to analysed -> pending_approval -> approved
        self.client.post(f"/api/v1/opportunities/{opp_id}/approve", headers=self._get_headers(self.alpha_owner_token), json={"note": "Approved for experiment"})

        # Create campaign and execute (moves opp to executing)
        camp_id = self._create_and_execute_campaign(self.alpha_owner_token, "tenant_store_alpha", opp_id=opp_id)

        # Check opp state is executing or completed
        opp_res = self.client.get(f"/api/v1/opportunities/{opp_id}", headers=self._get_headers(self.alpha_owner_token))
        self.assertIn(opp_res.json()["lifecycle_state"], ["executing", "completed"])

        # Create and evaluate experiment
        exp_res = self.client.post("/api/v1/experiments", headers=self._get_headers(self.alpha_owner_token), json={"campaign_id": camp_id})
        exp_id = exp_res.json()["experiment_id"]

        eval_res = self.client.post(f"/api/v1/experiments/{exp_id}/evaluate", headers=self._get_headers(self.alpha_owner_token), json={"end_experiment": True})
        self.assertEqual(eval_res.status_code, 200)

        # Check opp state has transitioned to 'evaluated'
        opp_after = self.client.get(f"/api/v1/opportunities/{opp_id}", headers=self._get_headers(self.alpha_owner_token))
        self.assertEqual(opp_after.json()["lifecycle_state"], "evaluated")

        # Verify opportunity_events contains 'evaluated'
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT to_state, reason FROM opportunity_events WHERE opportunity_id = ? ORDER BY occurred_at DESC", (opp_id,))
        latest_event = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(latest_event)
        self.assertEqual(latest_event[0], "evaluated")

    def test_06_minimum_sample_size_check_insufficient_data(self):
        """FR-050 & Section 16.5: Below minimum sample (sample < 100 or conversions < 5) returns 'insufficient_data'."""
        # Create a small experiment directly with 50 customers
        conn = get_db_connection()
        cursor = conn.cursor()
        exp_id = f"EXP-SMALL-{uuid.uuid4().hex[:6]}"
        camp_id = f"CAMP-SMALL-{uuid.uuid4().hex[:6]}"
        now_iso = "2026-10-30T12:00:00Z"

        cursor.execute("""
            INSERT INTO campaigns (campaign_id, tenant_id, objective, status, is_simulated, audience_size, created_at)
            VALUES (?, 'tenant_store_alpha', 'recover_abandoned_carts', 'completed', 1, 50, ?)
        """, (camp_id, now_iso))

        cursor.execute("""
            INSERT INTO experiments (experiment_id, tenant_id, campaign_id, holdout_pct, status, is_simulated, created_at)
            VALUES (?, 'tenant_store_alpha', ?, 20.0, 'running', 1, ?)
        """, (exp_id, camp_id, now_iso))

        # Assign only 10 control and 40 treatment customers (< 100 min per arm)
        uid = uuid.uuid4().hex[:6]
        for i in range(10):
            cursor.execute("""
                INSERT INTO experiment_assignments (assignment_id, experiment_id, tenant_id, customer_id, arm, assigned_at)
                VALUES (?, ?, 'tenant_store_alpha', ?, 'control', ?)
            """, (f"ASN-C-{uid}-{i}", exp_id, f"CUST-C-{uid}-{i}", now_iso))
        for i in range(40):
            cursor.execute("""
                INSERT INTO experiment_assignments (assignment_id, experiment_id, tenant_id, customer_id, arm, assigned_at)
                VALUES (?, ?, 'tenant_store_alpha', ?, 'treatment', ?)
            """, (f"ASN-T-{uid}-{i}", exp_id, f"CUST-T-{uid}-{i}", now_iso))

        conn.commit()
        conn.close()

        eval_res = self.client.post(f"/api/v1/experiments/{exp_id}/evaluate", headers=self._get_headers(self.alpha_owner_token), json={"end_experiment": True})
        self.assertEqual(eval_res.status_code, 200)
        results = eval_res.json()

        # Must report insufficient_data
        self.assertEqual(results["verdict"], "insufficient_data")
        self.assertFalse(results["sample_size_check"]["passed"])
        self.assertEqual(results["sample_size_check"]["status"], "insufficient_data")
        self.assertEqual(results["sample_size_check"]["control_progress_pct"], 10.0) # 10 / 100
        self.assertEqual(results["sample_size_check"]["treatment_progress_pct"], 40.0) # 40 / 100
        self.assertIn("below statistical threshold", results["verdict_reason"])

    def test_07_multi_tenant_isolation_on_experiments(self):
        """FR-061 & D-14: Tenant A experiment cannot be accessed or evaluated by Tenant B."""
        camp_id = self._create_and_execute_campaign(self.alpha_owner_token, "tenant_store_alpha")
        exp_res = self.client.post("/api/v1/experiments", headers=self._get_headers(self.alpha_owner_token), json={"campaign_id": camp_id})
        exp_id = exp_res.json()["experiment_id"]

        # Tenant B tries to get Tenant A experiment detail
        get_res = self.client.get(f"/api/v1/experiments/{exp_id}", headers=self._get_headers(self.beta_owner_token))
        self.assertEqual(get_res.status_code, 404)

        # Tenant B tries to evaluate Tenant A experiment
        eval_res = self.client.post(f"/api/v1/experiments/{exp_id}/evaluate", headers=self._get_headers(self.beta_owner_token))
        self.assertEqual(eval_res.status_code, 404)

    def test_08_get_experiment_results_endpoint(self):
        """GET /api/v1/experiments/{id}/results returns statistical report."""
        camp_id = self._create_and_execute_campaign(self.alpha_owner_token, "tenant_store_alpha")
        exp_res = self.client.post("/api/v1/experiments", headers=self._get_headers(self.alpha_owner_token), json={"campaign_id": camp_id})
        exp_id = exp_res.json()["experiment_id"]

        # Call results endpoint before finalizing (computes interim)
        interim_res = self.client.get(f"/api/v1/experiments/{exp_id}/results", headers=self._get_headers(self.alpha_owner_token))
        self.assertEqual(interim_res.status_code, 200)
        self.assertEqual(interim_res.json()["status"], "running")

        # Evaluate and finalize
        self.client.post(f"/api/v1/experiments/{exp_id}/evaluate", headers=self._get_headers(self.alpha_owner_token))

        # Call results endpoint after finalizing (returns stored report)
        final_res = self.client.get(f"/api/v1/experiments/{exp_id}/results", headers=self._get_headers(self.alpha_owner_token))
        self.assertEqual(final_res.status_code, 200)
        self.assertEqual(final_res.json()["status"], "completed")
        self.assertEqual(final_res.json()["verdict"], "treatment_wins")


if __name__ == "__main__":
    unittest.main()
