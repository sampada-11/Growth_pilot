"""
Redis-Backed Per-Tenant Rate Limiter (§3 Per-Tenant Rate Limiting)
Implements fixed/sliding window rate limiting scoped strictly by tenant_id.
Ensures one tenant's request volume cannot exhaust resources for another tenant.
"""
import time
from typing import Tuple
from fastapi import Request, HTTPException
from backend.app.integrations.redis_client import get_redis_client

RATE_LIMIT_PREFIX = "growthpilot:ratelimit:tenant:"


def is_tenant_rate_limited(
    tenant_id: str,
    route_name: str,
    max_requests: int = 15,
    window_seconds: int = 60
) -> Tuple[bool, int, int]:
    """
    Checks if a given tenant has exceeded the rate limit for a specific route.
    Returns: (is_limited: bool, remaining_requests: int, reset_seconds: int)
    """
    r = get_redis_client()
    key = f"{RATE_LIMIT_PREFIX}{route_name}:{tenant_id}"

    try:
        current = r.get(key)
        if current is None:
            r.set(key, "1", ex=window_seconds)
            return False, max_requests - 1, window_seconds

        count = int(current)
        if count >= max_requests:
            return True, 0, window_seconds

        new_count = r.incr(key)
        remaining = max(0, max_requests - new_count)
        return False, remaining, window_seconds
    except Exception as err:
        print(f"[RateLimiter] Error ({err}). Failing open.")
        return False, max_requests, window_seconds


# Backward-compatible alias
def is_rate_limited(
    identifier: str,
    route_name: str,
    max_requests: int = 15,
    window_seconds: int = 60
) -> Tuple[bool, int, int]:
    return is_tenant_rate_limited(
        tenant_id=identifier,
        route_name=route_name,
        max_requests=max_requests,
        window_seconds=window_seconds
    )


def enforce_tenant_rate_limit(
    tenant_id: str,
    route_name: str,
    max_requests: int = 15,
    window_seconds: int = 60
):
    """
    Raises HTTP 429 Too Many Requests if the tenant has exceeded their request quota.
    """
    is_limited, remaining, reset_secs = is_tenant_rate_limited(
        tenant_id=tenant_id,
        route_name=route_name,
        max_requests=max_requests,
        window_seconds=window_seconds
    )

    if is_limited:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too Many Requests",
                "message": f"Tenant '{tenant_id}' exceeded rate limit of {max_requests} requests per {window_seconds}s for '{route_name}'.",
                "tenant_id": tenant_id,
                "retry_after_seconds": reset_secs
            }
        )
