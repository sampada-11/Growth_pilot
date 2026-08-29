# GrowthPilot (AI Commerce Growth Agent) — Phase 2 Architecture

> *"Your business's AI growth team — it finds the opportunity, decides the play, and runs it."*

GrowthPilot is an autonomous multi-agent AI system for e-commerce sellers that closes the loop between analytics and action. Phase 2 introduces **Supabase Postgres** storage with multi-tenant isolation, **Row Level Security (RLS)**, **Redis event queue transport**, **Redis rate limiting**, and **30–60s caching**, alongside live **Razorpay Test-Mode** execution.

---

## 🌟 What's New in Phase 2

1. **Supabase Postgres & Multi-Tenant Schema**:
   - SQLAlchemy ORM models + Alembic versioned migrations (`alembic/versions/`).
   - `tenant_id` attached to all business data tables with demo tenant (`tenant_demo_001`).
   - Row Level Security (RLS) policies configured for PostgreSQL.
   - Dual-engine support: Supabase Postgres via `DATABASE_URL` with SQLite zero-ops local fallback.

2. **Redis Event Queue & Worker**:
   - Razorpay verified webhooks (`payment.captured`, `payment.failed`, `order.paid`) are published to the Redis event queue (`growthpilot:events:queue`).
   - Asynchronous Redis worker process consumes events and triggers the agent re-analysis pipeline without blocking webhook responses.
   - Zero-dependency local execution via automatic in-memory fallback if Redis server is offline.

3. **Redis Rate Limiting**:
   - Sliding-window rate limiter per client IP:
     - `/api/webhooks/razorpay`: 30 req/min
     - `/api/campaigns/{id}/approve`: 15 req/min
     - `/api/campaigns/{id}/execute`: 15 req/min
   - Rejects excessive bursts with HTTP `429 Too Many Requests`.

4. **Redis Caching (30–60s TTL)**:
   - High-throughput Redis caching for `/api/overview` and `/api/opportunities` (sub-millisecond repeat queries).
   - Dynamic cache invalidation triggered on agent pipeline runs or campaign executions.

5. **Dynamic Discount Band Guardrails**:
   - Deterministic `compute_discount_band(product, segment, opportunity)` calculating `(min_pct, max_pct, recommended_pct)` using product gross margin (`margin_pct`), inventory urgency factor, and customer CLV.
   - Dynamic ceiling replaces static 15% discount caps.

6. **End-to-End Razorpay Failure Handling**:
   - `payment.failed` event triggers an automated confidence penalty (-0.08) in the Decision Agent and records the failure in `executions` and `audit_logs` with a SHA-256 payload hash (sensitive card details are never stored).

---

## 🚀 Setup & Running

### 1. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set your Supabase and Razorpay credentials in `.env`:
```ini
DATABASE_URL=postgresql://postgres.yourprojectref:yourpassword@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require
REDIS_URL=redis://localhost:6379/0
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_key
DEMO_TENANT_ID=tenant_demo_001
```

### 2. Run Database Migrations (Supabase Postgres)

```bash
alembic upgrade head
```

### 3. Launch Application

```bash
python run_growthpilot.py
```
- Dashboard UI: **http://127.0.0.1:8000/**
- Interactive API Docs: **http://127.0.0.1:8000/docs**

---

## 🧪 Running Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```
Runs all 21 test suites across multi-agent orchestration, Razorpay test mode, Redis caching, rate limiting, and dynamic discount guardrails.
