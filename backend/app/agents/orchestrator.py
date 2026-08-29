"""
Orchestrator & Guardrail Agent (§13 & §14 Multi-Agent Architecture)
State Graph Coordinator and Execution Pipeline Manager with Multi-Tenant Scoping.
"""
import uuid
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.db.models import get_db_connection, log_audit
from backend.app.agents.insight_agent import run_insight_agent
from backend.app.agents.decision_agent import run_decision_agent
from backend.app.agents.campaign_agent import run_campaign_agent
from backend.app.agents.experiment_agent import evaluate_experiment
from backend.app.mock_api.marketing_api import execute_campaign_mock_api
from backend.app.tools.razorpay import create_razorpay_order, create_razorpay_payment_link
from backend.app.integrations.redis_client import invalidate_cache

def run_full_pipeline(tenant_id: str = "tenant_store_alpha") -> Dict[str, Any]:
    """
    Executes end-to-end multi-agent pipeline scoped to tenant_id:
    1. Insight Agent detects growth patterns for tenant
    2. Growth Decision Agent scores & ranks opportunities for tenant
    3. Campaign Agent drafts top-ranked campaign proposal for tenant
    """
    print(f"=== Starting GrowthPilot Multi-Agent Pipeline Run for {tenant_id} ===")
    
    # Step 1: Insight Agent
    insights = run_insight_agent(tenant_id=tenant_id)

    # Step 2: Growth Decision Agent
    opportunities = run_decision_agent(insights, tenant_id=tenant_id)

    # Step 3: Campaign Agent for top opportunity
    top_opp = opportunities[0] if opportunities else None
    campaign_proposal = None
    if top_opp:
        campaign_proposal = run_campaign_agent(top_opp, tenant_id=tenant_id)

    pipeline_state = {
        "tenant_id": tenant_id,
        "status": "completed_initial_analysis",
        "insights_count": len(insights),
        "opportunities_count": len(opportunities),
        "top_opportunity": top_opp,
        "active_campaign_proposal": campaign_proposal,
        "timestamp": datetime.now().isoformat()
    }

    log_audit("Orchestrator Agent", "PIPELINE_RUN_COMPLETED", pipeline_state, tenant_id=tenant_id)
    invalidate_cache(f"*{tenant_id}*")
    return pipeline_state


def approve_and_execute_campaign(
    campaign_id: str,
    approved_by: str = "Growth Manager",
    justification: Optional[str] = None,
    tenant_id: str = "tenant_store_alpha"
) -> Dict[str, Any]:
    """
    Handles human approval and triggers real Razorpay campaign execution scoped strictly to tenant_id.
    """
    print(f"[Orchestrator] Processing approval for campaign {campaign_id} by {approved_by} (Tenant: {tenant_id})...")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM campaign_proposals WHERE campaign_id = ? AND tenant_id = ?", (campaign_id, tenant_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Campaign proposal '{campaign_id}' not found for tenant '{tenant_id}'. Access denied.")

    campaign = dict(row)

    if campaign["risk_tier"] == "High" and not justification:
        conn.close()
        raise ValueError("High risk actions require an explicit human justification before execution.")

    token = f"TOKEN-EXEC-{uuid.uuid4().hex[:12].upper()}"

    base_price = 1200.0 if tenant_id == "tenant_store_alpha" else 1299.0
    offer_pct = float(campaign.get("offer_pct", 8.0))
    discounted_amount = base_price * (1.0 - (offer_pct / 100.0))

    execution_id = f"EXEC-{tenant_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        rzp_order = create_razorpay_order(
            amount_inr=discounted_amount,
            receipt_id=f"rec_{execution_id[:12]}",
            notes={"campaign_id": campaign_id, "approved_by": approved_by, "tenant_id": tenant_id}
        )

        rzp_link = create_razorpay_payment_link(
            amount_inr=discounted_amount,
            customer_id=f"CUST-{tenant_id[:4].upper()}-VIP",
            description=f"GrowthPilot {offer_pct:.0f}% Off Campaign Offer",
            campaign_id=campaign_id
        )

        rzp_order_id = rzp_order.get("id")
        rzp_link_id = rzp_link.get("id")
        exec_status = "executed"
        error_msg = None

        api_receipt = execute_campaign_mock_api(campaign, token)
        api_receipt["razorpay_order_id"] = rzp_order_id
        api_receipt["razorpay_payment_link"] = rzp_link.get("short_url")

    except Exception as err:
        exec_status = "failed"
        error_msg = str(err)
        rzp_order_id = None
        rzp_link_id = None
        api_receipt = {"status": "FAILED", "error": error_msg}

    cursor.execute("UPDATE campaign_proposals SET status = ? WHERE campaign_id = ? AND tenant_id = ?", (exec_status, campaign_id, tenant_id))

    cursor.execute("""
        INSERT INTO executions 
        (execution_id, tenant_id, campaign_id, approved_by, justification, executed_at, mock_api_status, execution_token, razorpay_order_id, razorpay_payment_link_id, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        execution_id, tenant_id, campaign_id, approved_by, justification or "Approved via Campaign Studio",
        datetime.now().isoformat(), api_receipt.get("status", "SENT"), token,
        rzp_order_id, rzp_link_id, exec_status, error_msg
    ))
    conn.commit()
    conn.close()

    log_audit(approved_by, "APPROVED_AND_EXECUTED", {
        "campaign_id": campaign_id,
        "execution_id": execution_id,
        "razorpay_order_id": rzp_order_id,
        "razorpay_payment_link_id": rzp_link_id,
        "status": exec_status
    }, tenant_id=tenant_id)

    exp_result = evaluate_experiment(execution_id) if exec_status == "executed" else None
    invalidate_cache(f"*{tenant_id}*")

    return {
        "execution_id": execution_id,
        "tenant_id": tenant_id,
        "campaign_id": campaign_id,
        "status": exec_status,
        "token": token,
        "razorpay_order_id": rzp_order_id,
        "razorpay_payment_link_id": rzp_link_id,
        "mock_api_receipt": api_receipt,
        "experiment_result": exp_result
    }
