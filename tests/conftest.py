"""
conftest.py — pytest / unittest bootstrap for GrowthPilot test suite.

Sets dummy environment variables so tests can import backend modules
without a real .env file.  Real integration tests that hit Razorpay or
Redis will still fall through to in-memory / test-mode fallbacks.

IMPORTANT — DB path alignment:
  models.py  uses a hardcoded DB_PATH relative to its own file location,
  always resolving to  data/growthpilot.db  in the repo root.
  DATABASE_URL must point to that same file so SQLAlchemy (database.py)
  and raw sqlite3 (models.py) both read/write the same database.
"""
import os
import pathlib

# ── Resolve repo root regardless of CWD ─────────────────────────────
_REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
_DB_PATH   = _REPO_ROOT / "data" / "growthpilot.db"

# ── Database — MUST match models.py DB_PATH exactly ─────────────────
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_PATH}")
os.environ.setdefault("DEMO_TENANT_ID", "tenant_store_alpha")

# ── Redis (in-memory fallback activates automatically when offline) ──
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# ── Razorpay — dummy keys trigger the in-process test-mode fallback ─
#    Keys starting with "rzp_test_growthpilot" are recognised by the
#    conditional in razorpay.py and bypass the live API entirely.
os.environ.setdefault("RAZORPAY_KEY_ID",        "rzp_test_growthpilot_DUMMY")
os.environ.setdefault("RAZORPAY_KEY_SECRET",     "DUMMY_RAZORPAY_SECRET")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "DUMMY_WEBHOOK_SECRET")

# ── Optional Gemini / LLM key ────────────────────────────────────────
os.environ.setdefault("GEMINI_API_KEY", "DUMMY_GEMINI_KEY")
