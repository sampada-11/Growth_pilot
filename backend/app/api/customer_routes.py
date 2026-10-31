"""
Customer Analytics API Routes
Prefix: /api/v1/customers
Supports:
- /api/v1/customers/analytics (RFM 6 segments, 5 visualizations)
- /api/v1/customers (Search, Filter, Sort, Pagination)
- /api/v1/customers/{customer_id} (Customer Detail Profile Modal)
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request

from backend.app.auth.dependencies import get_current_tenant
from backend.app.analytics.customer_analytics import (
    get_customer_analytics_summary,
    get_customers_paginated,
    get_customer_detail_profile
)

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("/analytics")
def api_get_customer_analytics(
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns 6-tier customer segmentation summary and 5 visualization datasets."""
    return get_customer_analytics_summary(tenant_id=tenant_id)


@router.get("")
def api_get_customers_table(
    request: Request,
    search: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    churn_tier: Optional[str] = Query(None),
    sort_by: str = Query("total_spent"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns paginated, searchable, sortable list of customers with RFM and Churn metrics."""
    return get_customers_paginated(
        tenant_id=tenant_id,
        search=search,
        segment=segment,
        churn_tier=churn_tier,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size
    )


@router.get("/{customer_id}")
def api_get_customer_detail(
    customer_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns deep customer profile with RFM metrics, order history, and recommended next action."""
    profile = get_customer_detail_profile(tenant_id=tenant_id, customer_id=customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found for active store.")
    return profile
