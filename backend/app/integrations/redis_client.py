"""
Redis Integration Manager (Event Queue, 30-60s Caching, Worker Processing)
Supports real Redis instances with automatic fallback to fakeredis / in-memory store.
"""
import os
import json
import time
import threading
from typing import Optional, Dict, Any, List
import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
EVENT_QUEUE_KEY = "growthpilot:events:queue"
CACHE_PREFIX = "growthpilot:cache:"

_redis_instance = None


def get_redis_client():
    """Returns a connected Redis client, using fakeredis fallback if server is offline."""
    global _redis_instance
    if _redis_instance is not None:
        return _redis_instance

    try:
        client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1.5)
        client.ping()
        _redis_instance = client
        print(f"[Redis] Connected to live Redis instance at {REDIS_URL}")
    except Exception as err:
        try:
            import fakeredis
            _redis_instance = fakeredis.FakeRedis(decode_responses=True)
            print("[Redis] Live Redis unavailable. Initialized in-memory FakeRedis instance for local/test execution.")
        except Exception:
            # Fallback simple dict client if fakeredis is missing
            class SimpleMockRedis:
                def __init__(self):
                    self.store = {}
                    self.lists = {}
                def ping(self): return True
                def get(self, k): return self.store.get(k)
                def set(self, k, v, ex=None): self.store[k] = v; return True
                def delete(self, *keys): 
                    for k in keys: self.store.pop(k, None)
                    return True
                def keys(self, pattern="*"): 
                    prefix = pattern.replace("*", "")
                    return [k for k in self.store if k.startswith(prefix)]
                def rpush(self, q, *values):
                    self.lists.setdefault(q, []).extend(values)
                    return len(self.lists[q])
                def lpop(self, q):
                    l = self.lists.get(q, [])
                    return l.pop(0) if l else None
                def pipeline(self): return self
                def execute(self): return []
                def incr(self, k):
                    v = int(self.store.get(k, 0)) + 1
                    self.store[k] = str(v)
                    return v
                def expire(self, k, ttl): return True
            _redis_instance = SimpleMockRedis()
            print("[Redis] Fallback SimpleMockRedis active.")

    return _redis_instance


# -------------------------------------------------------------
# Redis Caching (30 - 60 seconds TTL)
# -------------------------------------------------------------

def get_cached_json(cache_key: str) -> Optional[Any]:
    """Retrieves cached JSON object from Redis."""
    try:
        r = get_redis_client()
        raw = r.get(f"{CACHE_PREFIX}{cache_key}")
        if raw:
            return json.loads(raw)
    except Exception as err:
        print(f"[Redis Cache] Read error ({err})")
    return None


def set_cached_json(cache_key: str, data: Any, ttl_seconds: int = 45) -> bool:
    """Stores data in Redis with TTL (default 45s, configurable 30-60s)."""
    try:
        r = get_redis_client()
        key = f"{CACHE_PREFIX}{cache_key}"
        r.set(key, json.dumps(data), ex=ttl_seconds)
        return True
    except Exception as err:
        print(f"[Redis Cache] Write error ({err})")
        return False


def invalidate_cache(pattern: str = "*") -> int:
    """Invalidates cached keys matching pattern."""
    try:
        r = get_redis_client()
        full_pattern = f"{CACHE_PREFIX}{pattern}"
        keys = r.keys(full_pattern)
        if keys:
            r.delete(*keys)
            return len(keys)
    except Exception as err:
        print(f"[Redis Cache] Invalidation error ({err})")
    return 0


# -------------------------------------------------------------
# Redis Event Queue & Background Worker
# -------------------------------------------------------------

def enqueue_event(event_type: str, payload: Dict[str, Any]) -> str:
    """Pushes a verified event (e.g. Razorpay webhook) to the Redis event queue."""
    r = get_redis_client()
    event_packet = {
        "event_type": event_type,
        "payload": payload,
        "enqueued_at": time.time()
    }
    r.rpush(EVENT_QUEUE_KEY, json.dumps(event_packet))
    print(f"[Redis Queue] Enqueued event '{event_type}' to {EVENT_QUEUE_KEY}")
    return event_type


def pop_event() -> Optional[Dict[str, Any]]:
    """Pops the next event from the Redis queue."""
    r = get_redis_client()
    raw = r.lpop(EVENT_QUEUE_KEY)
    if raw:
        return json.loads(raw)
    return None


_worker_running = False

def start_redis_worker(poll_interval: float = 0.5):
    """Starts background worker thread to process queued events."""
    global _worker_running
    if _worker_running:
        return

    _worker_running = True

    def _worker_loop():
        from backend.app.agents.orchestrator import run_full_pipeline
        while _worker_running:
            try:
                event = pop_event()
                if event:
                    event_type = event.get("event_type")
                    print(f"[Redis Worker] Processing event '{event_type}' from queue...")
                    # Trigger orchestrator partial pipeline & invalidate cache
                    run_full_pipeline()
                    invalidate_cache("*")
                    print(f"[Redis Worker] Event '{event_type}' processed. Pipeline refreshed.")
                else:
                    time.sleep(poll_interval)
            except Exception as e:
                print(f"[Redis Worker] Worker error ({e})")
                time.sleep(poll_interval)

    thread = threading.Thread(target=_worker_loop, daemon=True)
    thread.start()
    print("[Redis Worker] Background event worker thread started.")
