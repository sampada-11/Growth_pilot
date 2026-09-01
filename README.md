# GrowthPilot (AI Commerce Growth Agent) — Phase 2 Architecture

> *"Your business's AI growth team — it finds the opportunity, decides the play, and runs it."*

GrowthPilot is an autonomous multi-agent AI system for e-commerce sellers that closes the loop between analytics and action. Phase 2 introduces **Supabase Postgres** storage with multi-tenant isolation, **Row Level Security (RLS)**, **Redis event queue transport**, **Redis rate limiting**, and **30–60s caching**, alongside live **Razorpay Test-Mode** execution.

---

## 🏗️ Architecture

![Architecture](docs/architecture_diagram.png)

The diagram shows the full Phase 2 stack:

| Layer | Components |
|---|---|
| **Client & Auth** | HTML5 Dashboard · Supabase JWT · `tenant_id` header |
| **FastAPI Gateway** | Per-tenant rate limiting · 30–60 s Redis cache · `get_current_tenant` dependency |
| **5-Agent AI Core** | Insight → Decision → Campaign & Pricing → Guardrail & Orchestrator → Experiment |
| **Storage** | Supabase Postgres (RLS, 12 tables, Alembic migrations) · SQLite offline fallback |
| **Event Bus** | Redis queue `growthpilot:events:queue` · Async background worker |
| **Payments** | Razorpay Test-Mode Orders · Payment Links · HMAC-SHA256 webhook verification |

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

> **Tip — local-only run (no Postgres / Redis needed):**  
> Leave `DATABASE_URL` pointing to SQLite (`sqlite:///./data/growthpilot.db`) and omit `REDIS_URL`. Both engines fall back automatically to in-process alternatives.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations (Supabase Postgres)

```bash
alembic upgrade head
```

### 4. Launch Application

```bash
python run_growthpilot.py
```
- Dashboard UI: **http://127.0.0.1:8000/**
- Interactive API Docs: **http://127.0.0.1:8000/docs**

---

## 📡 API Endpoints

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `POST` | `/auth/login` | JWT login with email + password | — |
| `POST` | `/auth/demo-login` | Instant demo tenant login (no password) | — |
| `POST` | `/auth/signup` | Register new tenant account | — |
| `GET`  | `/auth/me` | Current authenticated tenant profile | — |
| `GET`  | `/overview` | Business KPIs (revenue, GMV, churn) — Redis cached 45 s | — |
| `GET`  | `/customers/segments` | RFM customer segments for tenant | — |
| `GET`  | `/customers/churn-risk` | High-churn-risk customer list | — |
| `GET`  | `/products/trends` | Product velocity & inventory trends | — |
| `GET`  | `/opportunities` | Ranked growth opportunities — Redis cached 60 s | — |
| `GET`  | `/opportunities/{id}` | Single opportunity detail | — |
| `POST` | `/opportunities/{id}/campaign` | Generate campaign + pricing via AI agents | — |
| `GET`  | `/campaigns/{id}` | Campaign detail with guardrail status | — |
| `POST` | `/campaigns/{id}/approve` | Human-in-the-loop approval gate | 15 req/min |
| `POST` | `/campaigns/{id}/execute` | Dispatch campaign → Razorpay payment link | 15 req/min |
| `GET`  | `/experiments/{id}` | A/B experiment results & hypothesis verdict | — |
| `GET`  | `/audit-log` | Immutable audit trail (SHA-256 hashed payloads) | — |
| `POST` | `/pipeline/run` | Trigger full 5-agent analysis pipeline | — |
| `POST` | `/webhooks/razorpay` | **Razorpay webhook receiver** — HMAC-SHA256 verified; publishes `payment.captured` / `payment.failed` / `order.paid` to Redis event queue | 30 req/min |
| `POST` | `/razorpay/simulate-webhook` | Dev/test helper — simulates a signed Razorpay webhook locally | — |

---

## 🧪 Running Tests

### Prerequisites

**The test suite requires environment variables to be set.** Two options:

**Option A — use `.env` file (recommended for local runs):**
```bash
cp .env.example .env   # fill in real or test-mode Razorpay keys
python -m pytest tests/ -v
```

**Option B — run with dummy vars (CI / fresh clone, no credentials needed):**

`tests/conftest.py` is included in the repo and automatically injects safe dummy environment variables (SQLite DB + in-memory Redis fallback + dummy Razorpay keys) so that all 21 test cases can run without live credentials:

```bash
python -m pytest tests/ -v
```

Or with `unittest` directly:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

> **Note:** Tests that exercise the live Razorpay API (`test_01_create_razorpay_order`, `test_02_create_payment_link`) will operate in **test-mode simulation** when dummy keys are set — no real charges are made. Set real `rzp_test_*` keys in `.env` to validate against the Razorpay sandbox.

Runs all **21 test cases** across:
- Multi-agent orchestration
- Razorpay test-mode order & payment link creation
- HMAC-SHA256 webhook verification & SHA-256 payload hashing
- End-to-end `payment.failed` confidence penalty flow
- Redis event queue enqueue / pop
- Redis caching (30–60 s TTL) & invalidation
- Redis sliding-window rate limiting
- Supabase Postgres / SQLAlchemy tenant session
- Dynamic discount band guardrails
