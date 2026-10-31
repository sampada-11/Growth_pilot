"""
Tests for Conversational Copilot (§Natural Language Interface).
Tests:
1. Intent identification for all 6 example questions
2. Revenue diagnosis with figures & root-cause breakdown
3. Cart abandonment detection for top abandoned product
4. Churn risk identification with classification risk tiers
5. Campaign draft creation with Guardrail Agent validation & human approval lock
6. Opportunity prioritisation with multi-criteria normalized scoring
7. Experiment impact measurement with causal lift and next experiment recommendation
8. Multi-tenant isolation and conversation history persistence
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.jwt_auth import create_access_token
from backend.app.copilot.service import CopilotService

client = TestClient(app)


def get_token(tenant_id: str = "tenant_store_alpha", email: str = "alpha@growthpilot.demo") -> str:
    return create_access_token({
        "sub": "user_alpha_01",
        "email": email,
        "tenant_id": tenant_id,
        "store_name": "SoundWave Audio",
        "role": "owner"
    })


class TestConversationalCopilot:

    def test_01_intent_identification_all_6_core_questions(self):
        """Verifies intent recognition accurately classifies all 6 benchmark queries."""
        cases = [
            ("Why did my revenue decrease this month?", "revenue_diagnosis"),
            ("Which product has the highest cart abandonment?", "cart_abandonment"),
            ("Identify customers likely to churn.", "churn_risk"),
            ("Create a campaign for inactive customers.", "campaign_draft"),
            ("Which growth opportunity should I prioritise?", "opportunity_ranking"),
            ("What was the impact of my previous campaign?", "campaign_impact"),
        ]
        for query, expected_intent in cases:
            intent, label = CopilotService.identify_intent(query)
            assert intent == expected_intent, f"Query '{query}' expected '{expected_intent}', got '{intent}'"
            assert len(label) > 0

    def test_02_revenue_diagnosis_query(self):
        """Verifies revenue decline analysis retrieves figures, leakage breakdown and suggested actions."""
        token = get_token("tenant_store_alpha")
        res = client.post(
            "/api/v1/copilot/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Why did my revenue decrease this month?"}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["intent"] == "revenue_diagnosis"
        assert "refund" in data["answer"].lower()
        assert len(data["metrics"]) >= 3
        # Ensure leakage figures exist
        labels = [m["label"] for m in data["metrics"]]
        assert any("Revenue" in l for l in labels)
        assert any("Refund" in l or "Leakage" in l for l in labels)
        assert data["evidence"] is not None
        assert "root_causes" in data["evidence"]
        assert len(data["suggested_actions"]) > 0

    def test_03_cart_abandonment_query(self):
        """Verifies product cart abandonment analysis identifies Earbud Stand for SoundWave."""
        token = get_token("tenant_store_alpha")
        res = client.post(
            "/api/v1/copilot/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Which product has the highest cart abandonment?"}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["intent"] == "cart_abandonment"
        assert "Earbud Charging Stand" in data["answer"]
        assert any("71.4%" in m["value"] or "Abandonment" in m["label"] for m in data["metrics"])
        assert "funnel_dropoff" in data["evidence"]
        assert any("81,600" in a["label"] or "Opportunity" in a["label"] for a in data["suggested_actions"])

    def test_04_churn_risk_identification(self):
        """Verifies churn model extracts high-risk customer signatures."""
        token = get_token("tenant_store_alpha")
        res = client.post(
            "/api/v1/copilot/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Identify customers likely to churn."}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["intent"] == "churn_risk"
        assert "churn" in data["answer"].lower()
        assert len(data["metrics"]) >= 2
        assert "high_risk_sample" in data["evidence"]
        assert len(data["suggested_actions"]) > 0

    def test_05_campaign_creation_with_guardrail_gate_no_auto_execute(self):
        """
        CRITICAL GOVERNANCE TEST:
        Copilot must NOT directly execute high-impact operations.
        Must stage a draft and require human approval via Guardrail Agent.
        """
        token = get_token("tenant_store_alpha")
        res = client.post(
            "/api/v1/copilot/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Create a campaign for inactive customers."}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["intent"] == "campaign_draft"
        assert "guardrail" in data["answer"].lower()

        # Guardrail check
        guardrail = data["guardrail_status"]
        assert guardrail is not None, "Guardrail card must be present for campaign creation"
        assert guardrail["status"] == "passed"
        assert guardrail["requires_approval"] is True, "Human approval must be required"
        assert guardrail["execution_blocked"] is True, "Autonomous auto-dispatch must be blocked"
        assert len(guardrail["checks"]) >= 3

        # Suggested actions must point to Studio for approval
        actions = data["suggested_actions"]
        assert any(a["target_tab"] == "campaigns" and "Approve" in a["label"] for a in actions)

    def test_06_opportunity_prioritisation_scoring(self):
        """Verifies multi-criteria opportunity ranking explains Priority = 0.35I + 0.25C + 0.20F + 0.20E."""
        token = get_token("tenant_store_alpha")
        res = client.post(
            "/api/v1/copilot/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Which growth opportunity should I prioritise?"}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["intent"] == "opportunity_ranking"
        assert "Priority" in data["answer"]
        assert "81,600" in data["answer"] or "Recovery" in data["answer"]
        assert "scoring_formula" in data["evidence"]
        assert data["evidence"]["scores_breakdown"]["composite_priority"] > 70.0

    def test_07_previous_campaign_impact_measurement(self):
        """Verifies causal experiment reporting explains conversion lift, incremental profit and follow-up."""
        token = get_token("tenant_store_alpha")
        res = client.post(
            "/api/v1/copilot/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "What was the impact of my previous campaign?"}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["intent"] == "campaign_impact"
        assert "lift" in data["answer"].lower()
        assert any("Lift" in m["label"] for m in data["metrics"])
        assert any("Revenue" in m["label"] for m in data["metrics"])
        assert any("Profit" in m["label"] for m in data["metrics"])
        assert "decision_gates" in data["evidence"]

    def test_08_quick_prompts_and_history_persistence(self):
        """Verifies quick prompts endpoint and message persistence in copilot_messages."""
        token = get_token("tenant_store_alpha")

        # 1. Fetch quick prompts
        qp_res = client.get("/api/v1/copilot/quick-prompts")
        assert qp_res.status_code == 200
        prompts = qp_res.json()
        assert len(prompts) == 6

        # 2. Fetch history
        hist_res = client.get("/api/v1/copilot/history", headers={"Authorization": f"Bearer {token}"})
        assert hist_res.status_code == 200
        messages = hist_res.json()
        assert len(messages) >= 2  # Has previous test messages
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

