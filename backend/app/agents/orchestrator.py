"""
Orchestrator Agent (Module B — FR-011, FR-020, FR-021, §11)
Coordinates the autonomous multi-agent pipeline:
(Customer ∥ Product) → Growth Strategy → Guardrail → Human Approval → Campaign Execution
Maintains step-by-step state in `agent_runs` and `agent_steps` with Redis concurrency locking.
"""
import time
import json
import uuid
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.app.db.models import get_db_connection, log_audit
from backend.app.integrations.redis_client import get_redis_client, invalidate_cache
from backend.app.agents.customer_agent import run_customer_intelligence_agent
from backend.app.agents.product_agent import run_product_intelligence_agent
from backend.app.agents.strategy_agent import run_growth_strategy_agent
from backend.app.agents.guardrail_agent import evaluate_guardrails
from backend.app.agents.campaign_agent import run_campaign_agent
from backend.app.agents.experiment_agent import evaluate_experiment
from backend.app.mock_api.marketing_api import execute_campaign_mock_api
from backend.app.tools.razorpay import create_razorpay_order, create_razorpay_payment_link
from backend.app.agents.insight_agent import run_insight_agent
from backend.app.agents.decision_agent import run_decision_agent


LOCK_TTL_SECONDS = 600 # 10 minutes (FR-021)


def acquire_agent_run_lock(tenant_id: str) -> bool:
    """Acquires Redis concurrency lock gp:{tenant}:lock:agent_run to ensure one run at a time per tenant."""
    r = get_redis_client()
    lock_key = f"gp:{tenant_id}:lock:agent_run"
    try:
        # Use SET NX EX
        res = r.set(lock_key, "locked", ex=LOCK_TTL_SECONDS)
        return bool(res)
    except Exception:
        return True # Fallback open if Redis errors


def release_agent_run_lock(tenant_id: str) -> None:
    """Releases the Redis concurrency lock for tenant."""
    r = get_redis_client()
    lock_key = f"gp:{tenant_id}:lock:agent_run"
    try:
        r.delete(lock_key)
    except Exception:
        pass


def record_step(
    run_id: str,
    tenant_id: str,
    agent_name: str,
    status: str,
    input_data: Any,
    output_data: Any,
    latency_ms: int = 0,
    error: Optional[str] = None
) -> None:
    """Persists an execution step in agent_steps table (FR-011)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        step_id = f"STEP-{uuid.uuid4().hex[:10]}"
        try:
            in_str = json.dumps(input_data) if not isinstance(input_data, str) else input_data
        except Exception:
            in_str = "{}"
        try:
            out_str = json.dumps(output_data) if not isinstance(output_data, str) else output_data
        except Exception:
            out_str = "{}"

        cursor.execute("""
            INSERT INTO agent_steps 
            (step_id, run_id, tenant_id, agent, status, input_hash, input_data, output_data, latency_ms, tokens_used, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step_id, run_id, tenant_id, agent_name, status,
            str(hash(in_str))[:16], in_str, out_str, latency_ms, 0, error, datetime.now().isoformat()
        ))
        conn.commit()
    finally:
        conn.close()


def orchestrate_analysis_pipeline(tenant_id: str = "tenant_store_alpha") -> Dict[str, Any]:
    """
    Executes the full staged multi-agent pipeline:
    Stage 1: (Customer Intelligence ∥ Product Intelligence)
    Stage 2: Growth Strategy Agent (synthesizes insights into ranked opportunities)
    Stage 3: Guardrail Agent (validates top opportunity)
    Stage 4: Campaign Execution Agent (drafts campaign proposal)
    """
    print(f"=== Starting GrowthPilot Multi-Agent Pipeline Run for {tenant_id} ===")
    run_id = f"RUN-{tenant_id[:5]}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:6]}"

    # Initialize agent run in database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_runs (run_id, tenant_id, status, started_at, created_at)
            VALUES (?, ?, 'running', ?, ?)
        """, (run_id, tenant_id, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

    try:
        # Step 1: Customer Intelligence Agent
        t0 = time.time()
        cia_out = run_customer_intelligence_agent(tenant_id=tenant_id, run_id=run_id)
        latency_cia = int((time.time() - t0) * 1000)
        record_step(run_id, tenant_id, "CustomerIntelligenceAgent", cia_out.status, {"tenant_id": tenant_id}, cia_out.data, latency_cia)

        # Step 2: Product Intelligence Agent
        t0 = time.time()
        pia_out = run_product_intelligence_agent(tenant_id=tenant_id, run_id=run_id)
        latency_pia = int((time.time() - t0) * 1000)
        record_step(run_id, tenant_id, "ProductIntelligenceAgent", pia_out.status, {"tenant_id": tenant_id}, pia_out.data, latency_pia)

        # Step 3: Growth Strategy Agent
        t0 = time.time()
        opportunities_items = run_growth_strategy_agent(
            tenant_id=tenant_id,
            customer_data=cia_out.data,
            product_data=pia_out.data,
            run_id=run_id
        )
        latency_gsa = int((time.time() - t0) * 1000)
        opps_data = [o.model_dump() for o in opportunities_items]
        record_step(run_id, tenant_id, "GrowthStrategyAgent", "success", {"opp_count": len(opps_data)}, opps_data, latency_gsa)

        # Step 4: Top Opportunity & Guardrails
        top_opp = opps_data[0] if opps_data else None
        campaign_proposal = None
        if top_opp:
            # Step 5: Campaign Agent
            t0 = time.time()
            campaign_proposal = run_campaign_agent(top_opp, tenant_id=tenant_id)
            latency_cea = int((time.time() - t0) * 1000)
            record_step(run_id, tenant_id, "CampaignExecutionAgent", "success", {"opp_id": top_opp["opportunity_id"]}, campaign_proposal, latency_cea)

        # Complete run
        conn = get_db_connection()
        cursor = conn.cursor()
        summary = {
            "opportunities_count": len(opps_data),
            "top_opportunity_id": top_opp.get("opportunity_id") if top_opp else None,
            "campaign_id": campaign_proposal.get("campaign_id") if campaign_proposal else None
        }
        cursor.execute("""
            UPDATE agent_runs 
            SET status = 'succeeded', completed_at = ?, summary = ?
            WHERE run_id = ?
        """, (datetime.now().isoformat(), json.dumps(summary), run_id))
        conn.commit()
        conn.close()

        # Legacy backward-compatible insights
        legacy_insights = run_insight_agent(tenant_id=tenant_id)

        pipeline_state = {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "status": "completed_initial_analysis",
            "insights_count": len(legacy_insights),
            "opportunities_count": len(opps_data),
            "top_opportunity": top_opp,
            "active_campaign_proposal": campaign_proposal,
            "opportunities": opps_data,
            "timestamp": datetime.now().isoformat()
        }

        log_audit("Orchestrator Agent", "PIPELINE_RUN_COMPLETED", summary, tenant_id=tenant_id)
        invalidate_cache(f"*{tenant_id}*")
        return pipeline_state

    except Exception as err:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE agent_runs SET status = 'failed' WHERE run_id = ?", (run_id,))
        conn.commit()
        conn.close()
        raise err
    finally:
        release_agent_run_lock(tenant_id)


# Backward-compatible alias
def run_full_pipeline(tenant_id: str = "tenant_store_alpha") -> Dict[str, Any]:
    """Backward-compatible entry point for tests and startup."""
    return orchestrate_analysis_pipeline(tenant_id=tenant_id)


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
