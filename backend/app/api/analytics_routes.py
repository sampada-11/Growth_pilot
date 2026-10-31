"""
Versioned Analytics API Routes (Module A — FR-001 to FR-010, §B, §C, §D)
Base path: /api/v1/analytics/*
All endpoints require verified JWT and enforce multi-tenant isolation.
Supports date, product, and segment filters.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException, Request

from backend.app.auth.dependencies import get_current_tenant
from backend.app.analytics.service import (
    get_overview_analytics,
    get_revenue_trend_analytics,
    get_funnel_analytics,
    get_product_performance_analytics,
    get_purchase_patterns_analytics,
    get_filter_options,
    get_category_revenue_analytics,
    get_active_alerts_analytics,
    get_recent_activity_analytics
)
from backend.app.tools.segmentation import compute_customer_segmentation
from backend.app.tools.churn import compute_churn_risk_list
from backend.app.audit.service import record_audit_event

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def verify_no_tenant_override(request: Request, token_tenant: str):
    """Enforces that client-supplied tenant_id query/header cannot attempt to override JWT claim."""
    client_tenant = request.query_params.get("tenant_id")
    if client_tenant and client_tenant != token_tenant:
        record_audit_event(
            tenant_id=token_tenant,
            event_type="tenant.switch_denied",
            actor_id="client_gateway",
            actor_type="system",
            status="blocked",
            metadata={
                "attempted_tenant": client_tenant,
                "token_tenant": token_tenant,
                "url": str(request.url)
            }
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "FORBIDDEN_TENANT_OVERRIDE",
                    "message": "Client query param tenant_id does not match verified JWT token claims."
                }
            }
        )


@router.get("/overview")
def api_get_analytics_overview(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    from_date_alt: Optional[str] = Query(None, alias="from_date"),
    to_date_alt: Optional[str] = Query(None, alias="to_date"),
    segment_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    compare_previous: bool = Query(True),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns calculated KPIs (Revenue, Orders, AOV, Conversion Rate, Cart Abandonment, Retention, Growth) with deltas."""
    verify_no_tenant_override(request, tenant_id)
    eff_from = from_date or from_date_alt
    eff_to = to_date or to_date_alt
    return get_overview_analytics(
        tenant_id=tenant_id,
        from_date=eff_from,
        to_date=eff_to,
        segment_id=segment_id,
        product_id=product_id,
        compare_previous=compare_previous
    )


@router.get("/revenue-trend")
def api_get_revenue_trend(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    from_date_alt: Optional[str] = Query(None, alias="from_date"),
    to_date_alt: Optional[str] = Query(None, alias="to_date"),
    segment_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    interval: str = Query("day"),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns revenue time series for trend visualisations (daily/monthly)."""
    verify_no_tenant_override(request, tenant_id)
    eff_from = from_date or from_date_alt
    eff_to = to_date or to_date_alt
    return get_revenue_trend_analytics(
        tenant_id=tenant_id,
        from_date=eff_from,
        to_date=eff_to,
        segment_id=segment_id,
        product_id=product_id,
        interval=interval
    )


@router.get("/funnel")
def api_get_funnel(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    from_date_alt: Optional[str] = Query(None, alias="from_date"),
    to_date_alt: Optional[str] = Query(None, alias="to_date"),
    segment_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns conversion funnel steps: sessions → product_view → add_to_cart → checkout_started → order_paid."""
    verify_no_tenant_override(request, tenant_id)
    eff_from = from_date or from_date_alt
    eff_to = to_date or to_date_alt
    return get_funnel_analytics(
        tenant_id=tenant_id,
        from_date=eff_from,
        to_date=eff_to,
        segment_id=segment_id,
        product_id=product_id
    )


@router.get("/products")
def api_get_product_performance(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    from_date_alt: Optional[str] = Query(None, alias="from_date"),
    to_date_alt: Optional[str] = Query(None, alias="to_date"),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns per-product performance table with views, cart adds, abandonment rate, stock, and 30-day slope."""
    verify_no_tenant_override(request, tenant_id)
    eff_from = from_date or from_date_alt
    eff_to = to_date or to_date_alt
    return get_product_performance_analytics(
        tenant_id=tenant_id,
        from_date=eff_from,
        to_date=eff_to
    )


@router.get("/customers/rfm")
def api_get_customers_rfm(
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns customer RFM analysis, K-Means clustering, and historical/predictive CLV."""
    verify_no_tenant_override(request, tenant_id)
    return compute_customer_segmentation(tenant_id=tenant_id)


@router.get("/customers/churn-risk")
def api_get_customers_churn_risk(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns high churn risk customer list using classification model for tenant."""
    verify_no_tenant_override(request, tenant_id)
    return compute_churn_risk_list(tenant_id=tenant_id, limit=limit)


@router.get("/purchase-patterns")
def api_get_purchase_patterns(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns purchase frequency, median inter-purchase days, category affinity, and co-purchased pairs."""
    verify_no_tenant_override(request, tenant_id)
    return get_purchase_patterns_analytics(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date
    )


@router.get("/filter-options")
def api_get_filter_options(
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns available date ranges, customer segments, and products for filter controls (§D)."""
    verify_no_tenant_override(request, tenant_id)
    return get_filter_options(tenant_id=tenant_id)


@router.get("/category-revenue")
def api_get_category_revenue(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns category breakdown with revenue, units sold, and % share for Donut Chart."""
    verify_no_tenant_override(request, tenant_id)
    return get_category_revenue_analytics(tenant_id, from_date=from_date, to_date=to_date)


@router.get("/alerts")
def api_get_active_alerts(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns real-time actionable store alerts (high abandonment, low stock, churn risk, payment health)."""
    verify_no_tenant_override(request, tenant_id)
    return get_active_alerts_analytics(tenant_id, from_date=from_date, to_date=to_date)


@router.get("/recent-activity")
def api_get_recent_activity(
    request: Request,
    limit: int = Query(15, ge=1, le=50),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns unified recent business activity stream (orders, payments, campaign dispatches)."""
    verify_no_tenant_override(request, tenant_id)
    return get_recent_activity_analytics(tenant_id, limit=limit)
