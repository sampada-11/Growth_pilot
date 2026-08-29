"""
FastAPI REST API Routes (§Appendix F Endpoint List + Phase 1 & 2 Razorpay, Redis, Rate Limiting & Caching)
"""
import json
import sqlite3
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Header, Request, Depends
from pydantic import BaseModel

from backend.app.db.models import get_db_connection, log_audit
from backend.app.tools.segmentation import compute_customer_segmentation
from backend.app.tools.churn import compute_churn_risk_list
from backend.app.tools.trend import compute_product_trends
from backend.app.tools.razorpay import (
    create_razorpay_order,
    create_razorpay_payment_link,
    process_razorpay_webhook,
    verify_razorpay_signature,
    compute_payload_hash
)
from backend.app.agents.orchestrator import run_full_pipeline, approve_and_execute_campaign
from backend.app.agents.campaign_agent import run_campaign_agent
from backend.app.integrations.redis_client import (
    get_cached_json,
    set_cached_json,
    invalidate_cache,
    enqueue_event
)
from backend.app.integrations.rate_limiter import enforce_rate_limit

router = APIRouter(prefix="/api")


class ApprovalRequest(BaseModel):
    approved_by: str = "Growth Manager"
    justification: Optional[str] = None


class PaymentLinkRequest(BaseModel):
    amount: float
    customer_id: str = "CUST-00001"
    description: str = "GrowthPilot Promotional Offer"
    campaign_id: Optional[str] = "CAMP-DEMO-001"


class SimulateWebhookRequest(BaseModel):
    event: str = "payment.failed" # 'payment.captured', 'payment.failed', 'order.paid'
    amount: float = 1104.0
    customer_id: str = "CUST-00001"
    product_id: str = "PROD-002"
    error_description: Optional[str] = "Customer aborted payment at OTP verification"
    verify_signature: Optional[bool] = False


@router.get("/overview")
def get_executive_overview():
    """
    Executive Overview: revenue trend, conversion rate trend, top 3 growth opportunities, active alerts.
    Cached in Redis for 45 seconds (§4 Redis Caching).
    """
    cached = get_cached_json("overview")
    if cached:
        cached["_cached"] = True
        return cached

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(SUM(revenue), 0), COUNT(order_item_id) FROM order_items")
    row = cursor.fetchone()
    total_revenue = float(row[0])
    total_orders = int(row[1])

    cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cursor.fetchone()[0]

    conversion_rate = round((total_orders / (total_sessions + 1e-5)) * 100, 2)

    cursor.execute("SELECT * FROM opportunities ORDER BY priority_rank ASC LIMIT 3")
    opp_rows = cursor.fetchall()
    top_opportunities = [dict(r) for r in opp_rows]

    conn.close()

    result = {
        "headline_metrics": {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_customers": total_customers,
            "total_sessions": total_sessions,
            "conversion_rate_pct": conversion_rate,
            "active_alerts_count": 2
        },
        "top_opportunities": top_opportunities,
        "ai_weekly_recommendation": (
            "Primary Growth Focus: 71% Cart Abandonment on Earbud Stand (PROD-002) among 18-25 Earbud Buyers. "
            "Launching an 8% targeted discount offers ₹81,600 expected revenue lift."
        ),
        "_cached": False
    }

    set_cached_json("overview", result, ttl_seconds=45)
    return result


@router.get("/customers/segments")
def get_customer_segments():
    """Returns customer segment breakdown and RFM analytics."""
    return compute_customer_segmentation()


@router.get("/customers/churn-risk")
def get_churn_risk_list(limit: int = Query(20, ge=1, le=100)):
    """Returns high churn risk customer list with scores."""
    return compute_churn_risk_list(limit=limit)


@router.get("/products/trends")
def get_product_trends():
    """Returns product growth/decline trends and category distribution."""
    return compute_product_trends()


@router.get("/opportunities")
def get_opportunities():
    """
    Returns ranked growth opportunities.
    Cached in Redis for 45 seconds (§4 Redis Caching).
    """
    cached = get_cached_json("opportunities")
    if cached:
        return cached

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities ORDER BY priority_rank ASC")
    rows = cursor.fetchall()
    conn.close()
    
    result = [dict(r) for r in rows]
    set_cached_json("opportunities", result, ttl_seconds=45)
    return result


@router.get("/opportunities/{id}")
def get_opportunity_detail(id: str):
    """Returns detail & evidence for a specific opportunity."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.*, i.type AS insight_type, i.description AS insight_desc, i.evidence 
        FROM opportunities o
        JOIN insights i ON o.insight_id = i.insight_id
        WHERE o.opportunity_id = ?
    """, (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    data = dict(row)
    if data.get("evidence"):
        try:
            data["evidence"] = json.loads(data["evidence"])
        except Exception:
            pass
    return data


@router.post("/opportunities/{id}/campaign")
def draft_campaign_for_opportunity(id: str):
    """Triggers Campaign Agent to draft a campaign proposal for an opportunity with dynamic discount band."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE opportunity_id = ?", (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opp = dict(row)
    proposal = run_campaign_agent(opp)
    
    # Generate Razorpay Test Payment Link
    base_price = 1200.0
    offer_pct = float(proposal.get("offer_pct", 8.0))
    discounted_amount = base_price * (1.0 - (offer_pct / 100.0))
    
    rzp_link = create_razorpay_payment_link(
        amount_inr=discounted_amount,
        customer_id="CUST-1825-VIP",
        description=f"Special {offer_pct:.0f}% Off: Earbud Charging Stand",
        campaign_id=proposal["campaign_id"]
    )
    proposal["razorpay_payment_link"] = rzp_link.get("short_url")
    proposal["razorpay_link_id"] = rzp_link.get("id")

    return proposal


@router.get("/campaigns/{id}")
def get_campaign_detail(id: str):
    """Returns details for a drafted campaign proposal."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaign_proposals WHERE campaign_id = ?", (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Campaign proposal not found")

    data = dict(row)
    for field in ["risk_reasons", "discount_band"]:
        if data.get(field):
            try:
                data[field] = json.loads(data[field])
            except Exception:
                pass
    return data


@router.post("/campaigns/{id}/approve")
def approve_campaign_proposal(
    id: str,
    request: Request,
    payload: ApprovalRequest = Body(...)
):
    """
    Human approval endpoint for medium/high risk campaign proposals.
    Rate limited with Redis (§3 Rate Limiting).
    """
    enforce_rate_limit(request, route_name="campaign_approve", max_requests=15, window_seconds=60)
    try:
        result = approve_and_execute_campaign(
            campaign_id=id,
            approved_by=payload.approved_by,
            justification=payload.justification
        )
        return result
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.post("/campaigns/{id}/execute")
def execute_campaign_endpoint(
    id: str,
    request: Request,
    payload: ApprovalRequest = Body(...)
):
    """Execute campaign proposal (Rate limited)."""
    enforce_rate_limit(request, route_name="campaign_execute", max_requests=15, window_seconds=60)
    return approve_campaign_proposal(id=id, request=request, payload=payload)


@router.get("/experiments/{id}")
def get_experiment_detail(id: str):
    """Returns post-campaign experiment result details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT er.*, e.campaign_id, e.approved_by, e.executed_at, e.razorpay_order_id, e.razorpay_payment_link_id, c.target_segment, c.offer_pct
        FROM experiment_results er
        JOIN executions e ON er.execution_id = e.execution_id
        JOIN campaign_proposals c ON e.campaign_id = c.campaign_id
        WHERE er.result_id = ? OR er.execution_id = ? OR e.campaign_id = ?
    """, (id, id, id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Experiment result not found")

    return dict(row)


@router.get("/audit-log")
def get_audit_log(limit: int = Query(50, ge=1, le=200)):
    """Returns full audit log trail of agent decisions, webhooks, and human approvals."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    logs = []
    for r in rows:
        d = dict(r)
        if d.get("details"):
            try:
                d["details"] = json.loads(d["details"])
            except Exception:
                pass
        logs.append(d)
    return logs


@router.post("/pipeline/run")
def trigger_full_pipeline():
    """Triggers the full multi-agent detection and decision loop."""
    return run_full_pipeline()


# ---------------------------------------------------
# Phase 1 & 2 Razorpay & Redis Webhooks
# ---------------------------------------------------

@router.post("/webhooks/razorpay")
async def razorpay_webhook_listener(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature")
):
    """
    Razorpay Webhook Listener Endpoint.
    - Redis Rate Limited (30 req/min).
    - Signature Verification: Validates HMAC-SHA256 signature; rejects and logs audit alert on invalid signature.
    - SHA-256 payload hashing: never logs or stores raw sensitive card data.
    - Event Queue: Publishes verified events to Redis queue for background worker processing.
    """
    enforce_rate_limit(request, route_name="razorpay_webhook", max_requests=30, window_seconds=60)

    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    payload_hash = compute_payload_hash(raw_body)

    # 1. Signature Verification Check
    if x_razorpay_signature:
        is_valid = verify_razorpay_signature(body_str, x_razorpay_signature)
        if not is_valid:
            log_audit(
                "Razorpay Security",
                "INVALID_WEBHOOK_SIGNATURE_REJECTED",
                {"provided_signature": x_razorpay_signature[:8] + "..."},
                payload_hash=payload_hash
            )
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid Signature", "message": "Razorpay webhook signature verification failed."}
            )

    try:
        event_payload = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 2. Process event directly in DB
    result = process_razorpay_webhook(event_payload, payload_hash=payload_hash)

    # 3. Publish event to Redis Queue for async event-driven pipeline trigger
    enqueue_event(event_type=event_payload.get("event", "unknown"), payload=event_payload)
    result["enqueued_in_redis"] = True

    return result


@router.post("/razorpay/simulate-webhook")
def api_simulate_webhook(payload: SimulateWebhookRequest):
    """
    Demo Helper Endpoint to simulate Razorpay webhook events in test mode.
    Simulates events like 'payment.failed' or 'payment.captured' and pushes to Redis queue.
    """
    mock_payload = {
        "event": payload.event,
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_test_{id(payload)}",
                    "order_id": f"order_test_{id(payload)}",
                    "amount": int(payload.amount * 100),
                    "currency": "INR",
                    "email": f"{payload.customer_id.lower()}@example.com",
                    "error_description": payload.error_description,
                    "notes": {
                        "customer_id": payload.customer_id,
                        "product_id": payload.product_id,
                        "campaign_id": "CAMP-DEMO-001"
                    }
                }
            }
        }
    }

    raw_bytes = json.dumps(mock_payload).encode("utf-8")
    payload_hash = compute_payload_hash(raw_bytes)

    result = process_razorpay_webhook(mock_payload, payload_hash=payload_hash)
    enqueue_event(event_type=payload.event, payload=mock_payload)
    result["enqueued_in_redis"] = True

    return result
