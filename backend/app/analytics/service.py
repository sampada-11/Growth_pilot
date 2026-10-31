"""
Analytics Service Layer (Module A — FR-001, FR-003, FR-009, §B, §D)
Applies 60-second Redis caching with tenant-namespaced keys (gp:{tenant}:cache:analytics:...)
and orchestrates calls to pure engine functions with dynamic date, segment, and product filters.
"""
import hashlib
import json
from typing import Dict, Any, Optional, List

from backend.app.integrations.redis_client import get_redis_client
from backend.app.db.models import get_db_connection
from backend.app.analytics.engine import (
    compute_overview_kpis,
    compute_revenue_trend,
    compute_funnel_steps,
    compute_product_performance_list,
    compute_purchase_patterns,
    compute_category_revenue,
    compute_active_alerts,
    compute_recent_activity
)
from backend.app.tools.segmentation import compute_customer_segmentation
from backend.app.tools.churn import compute_churn_risk_list

CACHE_TTL_SECONDS = 60


def build_cache_key(tenant_id: str, endpoint: str, params: Dict[str, Any]) -> str:
    """Constructs tenant-namespaced Redis cache key per PRD conventions."""
    param_str = json.dumps(params, sort_keys=True)
    param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:12]
    return f"gp:{tenant_id}:cache:analytics:{endpoint}:{param_hash}"


def get_cached_analytics(cache_key: str) -> Optional[Any]:
    try:
        r = get_redis_client()
        val = r.get(cache_key)
        if val:
            data = json.loads(val)
            if isinstance(data, dict):
                data["_cached"] = True
            return data
    except Exception:
        pass
    return None


def set_cached_analytics(cache_key: str, data: Any, ttl: int = CACHE_TTL_SECONDS) -> None:
    try:
        r = get_redis_client()
        r.set(cache_key, json.dumps(data), ex=ttl)
    except Exception:
        pass


def invalidate_tenant_analytics_cache(tenant_id: str) -> None:
    """Invalidates all cached analytics queries for a specific tenant upon data ingestion."""
    try:
        r = get_redis_client()
        pattern = f"gp:{tenant_id}:cache:analytics:*"
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception:
        pass


# -------------------------------------------------------------------------
# Cached Service Endpoints
# -------------------------------------------------------------------------

def get_overview_analytics(
    tenant_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    segment_id: Optional[str] = None,
    product_id: Optional[str] = None,
    compare_previous: bool = True
) -> Dict[str, Any]:
    params = {"from": from_date, "to": to_date, "segment": segment_id, "product": product_id, "cmp": compare_previous}
    key = build_cache_key(tenant_id, "overview", params)
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_overview_kpis(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        segment_id=segment_id,
        product_id=product_id,
        compare_previous=compare_previous
    )
    result["_cached"] = False
    set_cached_analytics(key, result)
    return result


def get_revenue_trend_analytics(
    tenant_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    segment_id: Optional[str] = None,
    product_id: Optional[str] = None,
    interval: str = "day"
) -> Dict[str, Any]:
    params = {"from": from_date, "to": to_date, "segment": segment_id, "product": product_id, "interval": interval}
    key = build_cache_key(tenant_id, "revenue_trend", params)
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_revenue_trend(tenant_id, from_date, to_date, segment_id, product_id, interval)
    result["_cached"] = False
    set_cached_analytics(key, result)
    return result


def get_funnel_analytics(
    tenant_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    segment_id: Optional[str] = None,
    product_id: Optional[str] = None
) -> Dict[str, Any]:
    params = {"from": from_date, "to": to_date, "segment": segment_id, "product": product_id}
    key = build_cache_key(tenant_id, "funnel", params)
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_funnel_steps(tenant_id, from_date, to_date, segment_id, product_id)
    result["_cached"] = False
    set_cached_analytics(key, result)
    return result


def get_product_performance_analytics(
    tenant_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    params = {"from": from_date, "to": to_date}
    key = build_cache_key(tenant_id, "products", params)
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_product_performance_list(tenant_id, from_date, to_date)
    set_cached_analytics(key, result)
    return result


def get_purchase_patterns_analytics(
    tenant_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict[str, Any]:
    params = {"from": from_date, "to": to_date}
    key = build_cache_key(tenant_id, "purchase_patterns", params)
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_purchase_patterns(tenant_id, from_date, to_date)
    result["_cached"] = False
    set_cached_analytics(key, result)
    return result


def get_category_revenue_analytics(
    tenant_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict[str, Any]:
    params = {"from": from_date, "to": to_date}
    key = build_cache_key(tenant_id, "categories", params)
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_category_revenue(tenant_id, from_date, to_date)
    result["_cached"] = False
    set_cached_analytics(key, result)
    return result


def get_active_alerts_analytics(
    tenant_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    params = {"from": from_date, "to": to_date}
    key = build_cache_key(tenant_id, "alerts", params)
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_active_alerts(tenant_id, from_date, to_date)
    set_cached_analytics(key, result, ttl=30)
    return result


def get_recent_activity_analytics(
    tenant_id: str,
    limit: int = 15
) -> List[Dict[str, Any]]:
    # Dynamic real-time events cached for 10 seconds
    key = build_cache_key(tenant_id, "recent_activity", {"limit": limit})
    cached = get_cached_analytics(key)
    if cached:
        return cached

    result = compute_recent_activity(tenant_id, limit=limit)
    set_cached_analytics(key, result, ttl=10)
    return result


def get_filter_options(tenant_id: str) -> Dict[str, Any]:
    """Returns available date ranges, customer segments, and products for filter dropdowns (§D)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT segment FROM customers WHERE tenant_id = ? AND segment IS NOT NULL ORDER BY segment ASC", (tenant_id,))
    segments = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT product_id, name, category, COALESCE(price, base_price) as price FROM products WHERE tenant_id = ? ORDER BY name ASC", (tenant_id,))
    raw_products = [dict(r) for r in cursor.fetchall()]
    products = [
        {"product_id": p["product_id"], "name": p["name"], "title": p["name"], "category": p["category"], "price": p["price"]}
        for p in raw_products
    ]

    conn.close()

    return {
        "tenant_id": tenant_id,
        "date_presets": [
            {"id": "today", "label": "Today", "days": 1},
            {"id": "7d", "label": "Last 7 Days", "days": 7},
            {"id": "30d", "label": "Last 30 Days", "days": 30},
            {"id": "90d", "label": "Last 90 Days", "days": 90},
            {"id": "custom", "label": "Custom Range", "days": 0}
        ],
        "segments": ["All Segments"] + segments,
        "products": [{"product_id": "all", "name": "All Products", "title": "All Products", "category": "All"}] + products
    }
