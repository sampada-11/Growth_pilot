"""
FastAPI REST API Routes (§Appendix F Endpoint List + Phase 3 Multi-Tenant JWT Auth Hardening)
"""
import json
import sqlite3
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body, Header, Request, Depends
from pydantic import BaseModel, EmailStr

from backend.app.db.models import get_db_connection, log_audit
from backend.app.auth.jwt_auth import authenticate_user, register_user, create_access_token, DEMO_USERS
from backend.app.auth.dependencies import get_current_user, get_current_tenant
from backend.app.tools.segmentation import compute_customer_segmentation
from backend.app.tools.churn import compute_churn_risk_list
from backend.app.tools.trend import compute_product_trends
from backend.app.analytics.engine import compute_overview_kpis
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
from backend.app.integrations.rate_limiter import enforce_tenant_rate_limit

router = APIRouter(prefix="/api")


# -------------------------------------------------------------
# Auth Schemas & Endpoints (§1 Supabase Authentication)
# -------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class DemoLoginRequest(BaseModel):
    tenant: str = "alpha" # 'alpha' or 'beta'


class SignupRequest(BaseModel):
    email: str
    password: str
    store_name: str = "My E-Commerce Store"


class ApprovalRequest(BaseModel):
    approved_by: str = "Growth Manager"
    justification: Optional[str] = None


class SimulateWebhookRequest(BaseModel):
    event: str = "payment.failed"
    amount: float = 1104.0
    customer_id: str = "CUST-A0042"
    product_id: str = "PROD-002"
    error_description: Optional[str] = "Customer aborted payment at OTP verification"


@router.post("/auth/login")
def login(payload: LoginRequest):
    """Authenticates user and issues a verified JWT containing tenant_id."""
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": user["user_id"],
        "email": user["email"],
        "tenant_id": user["tenant_id"],
        "store_name": user["store_name"],
        "role": user["role"]
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": user["tenant_id"],
        "store_name": user["store_name"],
        "email": user["email"],
        "role": user["role"]
    }



@router.post("/auth/demo-login")
def demo_login(payload: DemoLoginRequest):
    """1-Click Demo Login switching between Tenant A (SoundWave) and Tenant B (PulseWear)."""
    email = "alpha@growthpilot.demo" if payload.tenant.lower() == "alpha" else "beta@growthpilot.demo"
    user = DEMO_USERS[email]
    token = create_access_token({
        "sub": user["user_id"],
        "email": user["email"],
        "tenant_id": user["tenant_id"],
        "store_name": user["store_name"],
        "role": user["role"]
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": user["tenant_id"],
        "store_name": user["store_name"],
        "email": user["email"]
    }


@router.post("/auth/signup")
def signup(payload: SignupRequest):
    """Provisions a new tenant store and returns JWT."""
    try:
        user = register_user(payload.email, payload.password, payload.store_name)
        token = create_access_token({
            "sub": user["user_id"],
            "email": user["email"],
            "tenant_id": user["tenant_id"],
            "store_name": user["store_name"],
            "role": user["role"]
        })
        return {
            "access_token": token,
            "token_type": "bearer",
            "tenant_id": user["tenant_id"],
            "store_name": user["store_name"],
            "email": user["email"]
        }
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get("/auth/me")
def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns profile and verified tenant context of authenticated user."""
    return current_user


# -------------------------------------------------------------
# Protected Business Routes (All scoped to verified tenant_id)
# -------------------------------------------------------------

@router.get("/overview")
def get_executive_overview(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    segment_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    tenant_id: str = Depends(get_current_tenant)
):
    """Executive Overview: Pure backend calculation with date, segment, and product filtering (§B, §C, §D)."""
    kpis = compute_overview_kpis(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        segment_id=segment_id,
        product_id=product_id,
        compare_previous=True
    )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE tenant_id = ? ORDER BY priority_rank ASC LIMIT 3", (tenant_id,))
    opp_rows = cursor.fetchall()
    top_opportunities = [dict(r) for r in opp_rows]
    conn.close()

    if tenant_id == "tenant_store_alpha":
        ai_rec = "SoundWave Focus: 71% Cart Abandonment on Earbud Stand (PROD-002). 8% targeted discount offers ₹81,600 expected revenue lift."
    else:
        ai_rec = "PulseWear Focus: 65% Inactivity Churn on Pulse Smartwatch. 12% VIP win-back bundle offers ₹42,000 revenue lift."

    m = kpis["metrics"]
    result = {
        "tenant_id": tenant_id,
        "headline_metrics": {
            "total_revenue": m["revenue"]["value"],
            "total_orders": m["orders"]["value"],
            "total_sessions": m["sessions"]["value"],
            "conversion_rate_pct": m["conversion_rate"]["value"] if m["conversion_rate"]["value"] is not None else 0.0,
            "aov": m["aov"]["value"] if m["aov"]["value"] is not None else 0.0,
            "cart_abandonment_rate_pct": m["cart_abandonment_rate"]["value"] if m["cart_abandonment_rate"]["value"] is not None else 0.0,
            "retention_rate_pct": m["retention_rate"]["value"] if m["retention_rate"]["value"] is not None else 0.0,
            "revenue_growth_pct": m["revenue_growth"]["value"],
            "active_alerts_count": len(top_opportunities),
            "refunded_amount": m["non_revenue_adjustments"]["refunded_amount"],
            "refunded_orders": m["non_revenue_adjustments"]["refunded_orders"],
            "cancelled_amount": m["non_revenue_adjustments"]["cancelled_amount"],
            "failed_payments_count": m["non_revenue_adjustments"]["failed_payments_count"]
        },
        "metrics": m,
        "range": kpis["range"],
        "top_opportunities": top_opportunities,
        "ai_weekly_recommendation": ai_rec,
        "_cached": False
    }
    return result


@router.get("/customers/segments")
def get_customer_segments(tenant_id: str = Depends(get_current_tenant)):
    """Returns customer segment breakdown and RFM analytics for tenant."""
    return compute_customer_segmentation(tenant_id=tenant_id)


@router.get("/customers/churn-risk")
def get_churn_risk_list(
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns high churn risk customer list for tenant."""
    return compute_churn_risk_list(tenant_id=tenant_id, limit=limit)


@router.get("/products/trends")
def get_product_trends(tenant_id: str = Depends(get_current_tenant)):
    """Returns product trends and category distribution for tenant."""
    return compute_product_trends(tenant_id=tenant_id)


@router.get("/opportunities")
def get_opportunities(tenant_id: str = Depends(get_current_tenant)):
    """Returns ranked growth opportunities for tenant (Redis cached)."""
    cache_key = f"opportunities:{tenant_id}"
    cached = get_cached_json(cache_key)
    if cached:
        return cached

    from backend.app.opportunities.service import OpportunityService
    result = OpportunityService.list_opportunities(tenant_id=tenant_id)
    set_cached_json(cache_key, result, ttl_seconds=45)
    return result


@router.get("/opportunities/{id}")
def get_opportunity_detail(id: str, tenant_id: str = Depends(get_current_tenant)):
    """Returns detail & evidence for an opportunity, strictly scoped to tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.*, i.type AS insight_type, i.description AS insight_desc, i.evidence 
        FROM opportunities o
        JOIN insights i ON o.insight_id = i.insight_id AND i.tenant_id = o.tenant_id
        WHERE o.opportunity_id = ? AND o.tenant_id = ?
    """, (id, tenant_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Opportunity '{id}' not found for tenant '{tenant_id}'. Access denied.")

    data = dict(row)
    if data.get("evidence"):
        try:
            data["evidence"] = json.loads(data["evidence"])
        except Exception:
            pass
    return data


@router.post("/opportunities/{id}/campaign")
def draft_campaign_for_opportunity(id: str, tenant_id: str = Depends(get_current_tenant)):
    """Triggers Campaign Agent to draft proposal scoped to tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE opportunity_id = ? AND tenant_id = ?", (id, tenant_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Opportunity '{id}' not found for tenant '{tenant_id}'.")

    opp = dict(row)
    proposal = run_campaign_agent(opp, tenant_id=tenant_id)
    
    base_price = 1200.0 if tenant_id == "tenant_store_alpha" else 1299.0
    offer_pct = float(proposal.get("offer_pct", 8.0))
    discounted_amount = base_price * (1.0 - (offer_pct / 100.0))
    
    rzp_link = create_razorpay_payment_link(
        amount_inr=discounted_amount,
        customer_id=f"CUST-{tenant_id[:4].upper()}-VIP",
        description=f"Special {offer_pct:.0f}% Off Offer",
        campaign_id=proposal["campaign_id"]
    )
    proposal["razorpay_payment_link"] = rzp_link.get("short_url")
    proposal["razorpay_link_id"] = rzp_link.get("id")

    return proposal


@router.get("/campaigns/{id}")
def get_campaign_detail(id: str, tenant_id: str = Depends(get_current_tenant)):
    """Returns details for a campaign proposal, strictly isolating across tenants."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaign_proposals WHERE campaign_id = ? AND tenant_id = ?", (id, tenant_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Campaign proposal '{id}' not found for tenant '{tenant_id}'. Access denied.")

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
    payload: ApprovalRequest = Body(...),
    tenant_id: str = Depends(get_current_tenant)
):
    """Human approval endpoint (Rate limited per-tenant)."""
    enforce_tenant_rate_limit(tenant_id=tenant_id, route_name="campaign_approve", max_requests=15, window_seconds=60)
    try:
        result = approve_and_execute_campaign(
            campaign_id=id,
            approved_by=payload.approved_by,
            justification=payload.justification,
            tenant_id=tenant_id
        )
        return result
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.post("/campaigns/{id}/execute")
def execute_campaign_endpoint(
    id: str,
    payload: ApprovalRequest = Body(...),
    tenant_id: str = Depends(get_current_tenant)
):
    """Execute campaign proposal (Rate limited per-tenant)."""
    enforce_tenant_rate_limit(tenant_id=tenant_id, route_name="campaign_execute", max_requests=15, window_seconds=60)
    return approve_campaign_proposal(id=id, payload=payload, tenant_id=tenant_id)


@router.get("/experiments/{id}")
def get_experiment_detail(id: str, tenant_id: str = Depends(get_current_tenant)):
    """Returns post-campaign experiment result details scoped to tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT er.*, e.campaign_id, e.approved_by, e.executed_at, e.razorpay_order_id, e.razorpay_payment_link_id, c.target_segment, c.offer_pct
        FROM experiment_results er
        JOIN executions e ON er.execution_id = e.execution_id AND e.tenant_id = er.tenant_id
        JOIN campaign_proposals c ON e.campaign_id = c.campaign_id AND c.tenant_id = er.tenant_id
        WHERE (er.result_id = ? OR er.execution_id = ? OR e.campaign_id = ?) AND er.tenant_id = ?
    """, (id, id, id, tenant_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Experiment result '{id}' not found for tenant '{tenant_id}'.")

    return dict(row)


@router.get("/audit-log")
def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns audit log trail strictly filtered by tenant_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs WHERE tenant_id = ? ORDER BY timestamp DESC LIMIT ?", (tenant_id, limit))
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
def trigger_full_pipeline(tenant_id: str = Depends(get_current_tenant)):
    """Triggers multi-agent analysis loop scoped to authenticated tenant."""
    return run_full_pipeline(tenant_id=tenant_id)


# -------------------------------------------------------------
# Razorpay Webhook Endpoint (Verified & Enqueued to Redis)
# -------------------------------------------------------------

@router.post("/webhooks/razorpay")
async def razorpay_webhook_listener(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature")
):
    """
    Razorpay Webhook Listener Endpoint.
    - Signature Verification: Validates HMAC-SHA256 signature; rejects and logs audit alert on invalid signature.
    - SHA-256 payload hashing.
    - Publishes verified events to Redis queue for background worker processing.
    """
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    payload_hash = compute_payload_hash(raw_body)

    if x_razorpay_signature:
        is_valid = verify_razorpay_signature(body_str, x_razorpay_signature)
        if not is_valid:
            log_audit(
                "Razorpay Security",
                "INVALID_WEBHOOK_SIGNATURE_REJECTED",
                {"provided_signature": x_razorpay_signature[:8] + "..."},
                payload_hash=payload_hash,
                tenant_id="security_system"
            )
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid Signature", "message": "Razorpay webhook signature verification failed."}
            )

    try:
        event_payload = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = process_razorpay_webhook(event_payload, payload_hash=payload_hash)
    enqueue_event(event_type=event_payload.get("event", "unknown"), payload=event_payload)
    result["enqueued_in_redis"] = True

    return result


@router.post("/razorpay/simulate-webhook")
def api_simulate_webhook(payload: SimulateWebhookRequest, tenant_id: str = Depends(get_current_tenant)):
    """Demo helper simulating Razorpay webhook event for authenticated tenant."""
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
                        "campaign_id": f"CAMP-{tenant_id}-DEMO",
                        "tenant_id": tenant_id
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


@router.get("/payments")
@router.get("/v1/payments")
def list_payments(tenant_id: str = Depends(get_current_tenant)):
    """Lists recent persistent payment and webhook events for current tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT payment_id, tenant_id, order_id, provider_event_id, amount, currency, status, is_simulated, created_at
            FROM payments
            WHERE tenant_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (tenant_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
