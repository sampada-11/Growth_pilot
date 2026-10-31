"""
Product Intelligence & Catalog Analytics Routes
Base path: /api/v1/products/*
All endpoints require verified JWT and enforce multi-tenant isolation.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException, Request

from backend.app.auth.dependencies import get_current_tenant
from backend.app.analytics.product_analytics import (
    compute_product_analytics_bundle,
    get_product_detail_analytics
)

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("/analytics")
def api_get_product_analytics(
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    from_date_alt: Optional[str] = Query(None, alias="from_date"),
    to_date_alt: Optional[str] = Query(None, alias="to_date"),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Returns full product analytics bundle:
    - Summary (catalog revenue, units sold, avg margin, gross profit)
    - Revenue by product (bar chart)
    - Sales trends (multi-product daily line chart)
    - Profit margin analysis (cost, profit per unit, margin tier)
    - Top selling products
    - Underperforming products with root-cause diagnosis & AI actions
    - Category distribution (donut chart)
    - Product performance matrix (4-quadrant scatter)
    - Inventory alerts (strictly when inventory data exists)
    """
    eff_from = from_date or from_date_alt
    eff_to = to_date or to_date_alt
    return compute_product_analytics_bundle(
        tenant_id=tenant_id,
        from_date=eff_from,
        to_date=eff_to
    )


@router.get("/inventory-alerts")
def api_get_inventory_alerts(
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns inventory alerts ONLY when inventory tracking data exists."""
    bundle = compute_product_analytics_bundle(tenant_id=tenant_id)
    return {
        "has_inventory_data": bundle["has_inventory_data"],
        "alerts": bundle["inventory_alerts"]
    }


@router.get("/{product_id}")
def api_get_product_detail(
    product_id: str,
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns deep profile for a single clicked product (demographics, funnel, trend, recommended action)."""
    detail = get_product_detail_analytics(
        tenant_id=tenant_id,
        product_id=product_id,
        from_date=from_date,
        to_date=to_date
    )
    if not detail:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found for tenant '{tenant_id}'.")
    return detail
