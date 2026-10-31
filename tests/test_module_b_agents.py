"""
Phase 3 Test Suite: Module B — Multi-Agent System & LLM Client Wrapper
Validates FR-011 through FR-022: LLM wrapper, Pydantic schemas, CIA, PIA, GSA, GRA, CEA, and Orchestrator.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.jwt_auth import DEMO_USERS, create_access_token
from backend.app.db.seed_synthetic_data import seed_database
from backend.app.agents.llm_client import generate_llm_response
from backend.app.agents.customer_agent import run_customer_intelligence_agent
from backend.app.agents.product_agent import run_product_intelligence_agent
from backend.app.agents.guardrail_agent import evaluate_guardrails
from backend.app.agents.strategy_agent import run_growth_strategy_agent, calculate_opportunity_impact
from backend.app.agents.orchestrator import orchestrate_analysis_pipeline
from backend.app.db.models import get_db_connection


@pytest.fixture(scope="module")
def seeded_db():
    seed_database(force=False)


@pytest.fixture
def client(seeded_db):
    return TestClient(app)


@pytest.fixture
def alpha_headers():
    user = DEMO_USERS["alpha@growthpilot.demo"]
    token = create_access_token({
        "sub": user["user_id"],
        "email": user["email"],
        "tenant_id": user["tenant_id"],
        "store_name": user["store_name"],
        "role": user["role"]
    })
    return {"Authorization": f"Bearer {token}"}


class TestModuleBAgents:

    def test_01_llm_client_mock_mode_and_audit(self):
        """Verifies LLM wrapper produces structured output, badges is_simulated=true, and audits."""
        resp = generate_llm_response(
            prompt="Analyze cart abandonment",
            tenant_id="tenant_store_alpha",
            agent_name="TestAgent"
        )
        assert resp.is_simulated is True
        assert resp.content is not None
        assert resp.latency_ms >= 0

        # Check audit event written
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE agent_or_user = 'TestAgent'")
        row = cursor.fetchone()
        conn.close()
        assert row is not None

    def test_02_customer_intelligence_agent_rfm_and_churn(self):
        """Verifies CIA computes RFM quintiles (1-5), segments, and churn scores."""
        cia_out = run_customer_intelligence_agent(tenant_id="tenant_store_alpha")
        assert cia_out.agent == "CustomerIntelligenceAgent"
        assert cia_out.status == "success"

        data = cia_out.data
        assert "segments" in data
        assert len(data["segments"]) > 0

        assert "rfm" in data
        assert len(data["rfm"]) > 0
        first_rfm = data["rfm"][0]
        assert 1 <= first_rfm["R"] <= 5
        assert 1 <= first_rfm["F"] <= 5
        assert 1 <= first_rfm["M"] <= 5
        assert first_rfm["segment"] in [
            "Champions", "Loyal Customers", "At Risk", "Hibernating", "New Customers", "Potential Loyalists"
        ]

        assert "churn_risk" in data
        assert len(data["churn_risk"]) > 0
        for c in data["churn_risk"][:5]:
            assert 0.0 <= c["score"] <= 1.0
            assert c["method"] in ["heuristic", "model"]

    def test_03_product_intelligence_agent_anomaly_detection(self):
        """Verifies PIA ranks catalog and flags PROD-002 Earbud Stand abandonment anomaly."""
        pia_out = run_product_intelligence_agent(tenant_id="tenant_store_alpha")
        assert pia_out.agent == "ProductIntelligenceAgent"
        assert pia_out.status == "success"

        data = pia_out.data
        assert "ranking" in data
        assert len(data["ranking"]) > 0

        # PROD-002 flagged as problem product due to cart abandonment
        problem_prods = data["problem_products"]
        prod_002_issue = next((p for p in problem_prods if p["product_id"] == "PROD-002"), None)
        assert prod_002_issue is not None
        assert prod_002_issue["issue"] == "high_cart_abandonment"

    def test_04_guardrail_rules_gr01_to_gr09(self):
        """Validates deterministic Guardrail Agent rules GR-01 through GR-09."""
        tenant_id = "tenant_store_alpha"
        prod_info = {"base_price": 1200.0, "margin_pct": 50.0, "unit_cost": 600.0}

        # 1. Valid proposal (8% discount) -> REQUIRE_APPROVAL (GR-06)
        res_valid = evaluate_guardrails(
            proposal={"offer_pct": 8.0, "segment_size": 850, "estimated_cost": 11424.0, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            product_info=prod_info
        )
        assert res_valid.decision == "REQUIRE_APPROVAL"
        assert res_valid.risk_tier == "Medium"
        assert res_valid.can_auto_execute is False

        # 2. GR-01: Discount > 20% -> BLOCK
        res_gr01 = evaluate_guardrails(
            proposal={"offer_pct": 25.0, "segment_size": 100, "estimated_cost": 1000.0, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            product_info=prod_info
        )
        assert res_gr01.decision == "BLOCK"
        assert any(r.id == "GR-01" and not r.passed for r in res_gr01.rules)

        # 3. GR-02: Margin floor breach (Post-discount margin < 15%)
        # Base price 1000, unit cost 800 (20% margin). Discount of 10% -> price 900. Margin: (900-800)/900 = 11.1% < 15%
        res_gr02 = evaluate_guardrails(
            proposal={"offer_pct": 10.0, "segment_size": 100, "estimated_cost": 1000.0, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            product_info={"base_price": 1000.0, "unit_cost": 800.0, "margin_pct": 20.0}
        )
        assert res_gr02.decision == "BLOCK"
        assert any(r.id == "GR-02" and not r.passed for r in res_gr02.rules)

        # 4. GR-03: Budget cap breach (> 50,000)
        res_gr03 = evaluate_guardrails(
            proposal={"offer_pct": 5.0, "segment_size": 1000, "estimated_cost": 65000.0, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            product_info=prod_info
        )
        assert res_gr03.decision == "BLOCK"
        assert any(r.id == "GR-03" and not r.passed for r in res_gr03.rules)

        # 5. GR-07: Content safety (banned phrase)
        res_gr07 = evaluate_guardrails(
            proposal={
                "offer_pct": 5.0,
                "segment_size": 100,
                "estimated_cost": 500.0,
                "tenant_id": tenant_id,
                "copy_text": "Sign up now for 100% guaranteed returns in 5 minutes!"
            },
            tenant_id=tenant_id,
            product_info=prod_info
        )
        assert res_gr07.decision == "BLOCK"
        assert any(r.id == "GR-07" and not r.passed for r in res_gr07.rules)

        # 6. GR-09: Tenant mismatch
        res_gr09 = evaluate_guardrails(
            proposal={"offer_pct": 5.0, "segment_size": 100, "estimated_cost": 500.0, "tenant_id": "tenant_store_beta"},
            tenant_id=tenant_id,
            product_info=prod_info
        )
        assert res_gr09.decision == "BLOCK"
        assert any(r.id == "GR-09" and not r.passed for r in res_gr09.rules)

    def test_05_growth_strategy_deterministic_impact_and_priority(self):
        """Verifies Section 16.6 impact formula (850 * 0.08 * 1200 = ₹81,600) and priority formula."""
        rev_impact, profit_impact, inputs = calculate_opportunity_impact(
            audience_size=850,
            base_price=1200.0,
            baseline_conversion_pct=6.0,
            expected_conversion_pct=14.0,
            margin_pct=50.0,
            discount_pct=8.0
        )
        assert rev_impact == 81600.0
        assert inputs["incremental_buyers"] == 68
        assert profit_impact > 0

        # Execute GSA
        opps = run_growth_strategy_agent(
            tenant_id="tenant_store_alpha",
            customer_data={},
            product_data={}
        )
        assert len(opps) > 0
        top = opps[0]
        assert top.opportunity_id == "OPP-tenant_store_alpha-001"
        assert top.est_revenue_impact == 81600.0
        # Priority score = 81600 * 0.78 * 1.25 = 79560.0
        assert top.priority_score == pytest.approx(79560.0, rel=1e-2)
        assert top.lifecycle_state == "analysed"

    def test_06_orchestrator_pipeline_and_step_persistence(self, client, alpha_headers):
        """Verifies full orchestrated run records agent_runs and agent_steps, and API exposes them."""
        # Trigger orchestrator via POST /api/v1/agents/runs
        res = client.post("/api/v1/agents/runs", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert "run_id" in data
        run_id = data["run_id"]
        assert data["status"] == "completed_initial_analysis"
        assert data["opportunities_count"] > 0

        # Check run details from GET /api/v1/agents/runs/{id}
        res_detail = client.get(f"/api/v1/agents/runs/{run_id}", headers=alpha_headers)
        assert res_detail.status_code == 200
        run_data = res_detail.json()
        assert run_data["run_id"] == run_id
        assert run_data["status"] == "succeeded"

        # Check steps persisted
        steps = run_data["steps"]
        assert len(steps) >= 3
        agent_names = [s["agent"] for s in steps]
        assert "CustomerIntelligenceAgent" in agent_names
        assert "ProductIntelligenceAgent" in agent_names
        assert "GrowthStrategyAgent" in agent_names

    def test_07_dry_run_guardrails_api(self, client, alpha_headers):
        """Verifies /api/v1/guardrails/validate evaluates proposal without mutating database."""
        payload = {
            "offer_pct": 8.0,
            "segment_size": 850,
            "estimated_cost": 11424.0,
            "tenant_id": "tenant_store_alpha"
        }
        res = client.post("/api/v1/guardrails/validate", json=payload, headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert "decision" in data
        assert "rules" in data
        assert len(data["rules"]) == 9

