"""
conftest.py — pytest / unittest bootstrap for GrowthPilot test suite.

Sets dummy environment variables so tests can import backend modules
without a real .env file.  Real integration tests that hit Razorpay or
Redis will still fall through to in-memory / test-mode fallbacks.
"""
import os

# ── Database ──────────────────────────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/growthpilot_test.db")
os.environ.setdefault("DEMO_TENANT_ID", "tenant_demo_001")

# ── Redis (in-memory fallback activates automatically when offline) ───
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# ── Razorpay test-mode keys ───────────────────────────────────────────
os.environ.setdefault("RAZORPAY_KEY_ID",        "rzp_test_DUMMY_KEY_ID")
os.environ.setdefault("RAZORPAY_KEY_SECRET",     "DUMMY_RAZORPAY_SECRET")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "DUMMY_WEBHOOK_SECRET")

# ── Optional Gemini / LLM key ─────────────────────────────────────────
os.environ.setdefault("GEMINI_API_KEY", "DUMMY_GEMINI_KEY")
