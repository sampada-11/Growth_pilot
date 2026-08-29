"""
Redis-Backed Rate Limiter (§3 Rate Limiting)
Implements fixed/sliding window rate limiting per IP and per route.
"""
import time
from typing import Tuple
from fastapi import Request, HTTPException
from backend.app.integrations.redis_client import get_redis_client

RATE_LIMIT_PREFIX = "growthpilot:ratelimit:"


def is_rate_limited(
    identifier: str,
    route_name: str,
    max_requests: int = 30,
    window_seconds: int = 60
) -> Tuple[bool, int, int]:
    """
    Checks if a given identifier (IP/client) has exceeded rate limit for a specific route.
    Returns: (is_limited: bool, remaining_requests: int, reset_seconds: int)
    """
    r = get_redis_client()
    key = f"{RATE_LIMIT_PREFIX}{route_name}:{identifier}"

    try:
        current = r.get(key)
        if current is None:
            # First request in this window
            r.set(key, "1", ex=window_seconds)
            return False, max_requests - 1, window_seconds

        count = int(current)
        if count >= max_requests:
            return True, 0, window_seconds

        # Increment count
        new_count = r.incr(key)
        remaining = max(0, max_requests - new_count)
        return False, remaining, window_seconds
    except Exception as err:
        print(f"[RateLimiter] Error ({err}). Failing open.")
        return False, max_requests, window_seconds


def enforce_rate_limit(
    request: Request,
    route_name: str,
    max_requests: int = 30,
    window_seconds: int = 60
):
    """
    FastAPI dependency/helper to enforce rate limits and raise 429 if exceeded.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Support forwarded header if behind proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    is_limited, remaining, reset_secs = is_rate_limited(
        identifier=client_ip,
        route_name=route_name,
        max_requests=max_requests,
        window_seconds=window_seconds
    )

    if is_limited:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too Many Requests",
                "message": f"Rate limit of {max_requests} requests per {window_seconds}s exceeded for route '{route_name}'.",
                "retry_after_seconds": reset_secs
            }
        )
