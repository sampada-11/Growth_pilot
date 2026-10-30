# 🚀 GrowthPilot — Autonomous AI Commerce Growth Agent System

> *"Your business's AI growth team — it finds the opportunity, decides the play, and runs it."*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E.svg?style=flat&logo=supabase&logoColor=white)](https://supabase.com/)
[![Redis](https://img.shields.io/badge/Redis-Queue%20%26%20Cache-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Razorpay](https://img.shields.io/badge/Razorpay-Test--Mode%20Rails-0C2340.svg?style=flat&logo=razorpay&logoColor=white)](https://razorpay.com/)
[![Tests](https://img.shields.io/badge/Tests-28%20Passed-brightgreen.svg?style=flat)](#-testing--validation)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat)](LICENSE)

---

## 📖 Table of Contents
- [Executive Summary](#-executive-summary)
- [The Problem: The Analytics-to-Action Gap](#-the-problem-the-analytics-to-action-gap)
- [System Architecture](#-system-architecture)
- [5-Agent Multi-Agent AI Core](#-5-agent-multi-agent-ai-core)
- [Mathematical Rigor & Zero Hallucination](#-mathematical-rigor--zero-hallucination)
- [Multi-Tenant Architecture & Security](#-multi-tenant-architecture--security)
- [Live Razorpay Rails & Event Loop](#-live-razorpay-rails--event-loop)
- [Database Schema (12 Tables)](#-database-schema-12-relational-tables)
- [Single-Page Interactive Dashboard](#-single-page-interactive-dashboard)
- [Quickstart & Setup](#-quickstart--setup)
- [Complete API Reference](#-complete-api-reference)
- [Testing & Validation](#-testing--validation)
- [Directory Structure](#-directory-structure)

---

## 🎯 Executive Summary

**GrowthPilot** is an autonomous, multi-agent AI software system designed for e-commerce merchants and D2C brands. It closes the loop between **business intelligence and commercial action**. 

Unlike conventional dashboards that only display historical statistics, GrowthPilot:
1. **Scans store telemetry** (customer sessions, cart additions, abandonment rates, order histories).
2. **Detects high-value bottlenecks** using statistical churn propensity models.
3. **Mathematically scores and ranks opportunities** using priority scoring (Impact × Confidence × Urgency).
4. **Calculates margin-safe dynamic discount bands** to prevent margin cannibalization.
5. **Classifies proposals by risk tier** and enforces human-in-the-loop approval.
6. **Executes live Razorpay orders and payment links** upon approval.
7. **Monitors webhooks asynchronously via Redis** and validates conversion lift via **two-proportion Z-tests**.

---

## ⚡ The Problem: The Analytics-to-Action Gap

Modern e-commerce platforms generate massive volumes of telemetry, but merchants face a critical operational dilemma:

```
┌─────────────────────────────────┐
│     Traditional Analytics       │  ❌ Passive & Descriptive
│ "Cart abandonment is 71% for    │     Leaves merchant guessing what offer,
│  Earbud Stands among VIPs"      │     what segment, and what price to set.
└────────────────┬────────────────┘
                 │
        [ANALYTICS-TO-ACTION GAP]
                 │
┌────────────────▼────────────────┐
│      GrowthPilot Solution       │  ✅ Prescriptive, Guardrailed & Executable
│ Autonomous 5-agent pipeline     │     Calculates margin-safe 8% discount,
│ that drafts, gates, and creates │     requests 1-click human approval, and
│ live Razorpay checkout links.   │     creates instant payment links.
└─────────────────────────────────┘
```

---

## 🏗️ System Architecture

GrowthPilot is engineered around a **4-Tier Enterprise Architecture** combining asynchronous gateway processing, multi-tenant database isolation, an in-memory event bus, and deterministic agent orchestration.

![System Architecture](docs/architecture_diagram.png)

### Architectural Tiers

| Tier | Layer | Technologies | Responsibilities |
|---|---|---|---|
| **Tier 1** | **Client & Presentation** | HTML5, Tailwind CSS, Chart.js, Vanilla JS | Multi-view responsive merchant portal, session-based JWT storage, 1-click demo tenant context switching. |
| **Tier 2** | **Gateway & Protection** | FastAPI, PyJWT, Sliding-Window Limiter | Strict server-side JWT verification (`get_current_tenant`), per-tenant rate limiting (15-30 req/min), sub-millisecond Redis caching (30–60s TTL). |
| **Tier 3** | **Multi-Agent Core** | Python, NumPy, Pandas, Scipy Stats | 5-agent pipeline: Insight → Decision → Campaign & Pricing → Guardrail & Orchestrator → Experiment. |
| **Tier 4** | **Persistence & Rails** | Supabase Postgres, SQLite WAL, Redis, Razorpay | Row Level Security (RLS) policies, Redis event queue (`growthpilot:events:queue`), background worker, Razorpay Orders & Payment Links. |

---

## 🤖 5-Agent Multi-Agent AI Core

GrowthPilot distributes complex commercial operations across 5 specialized autonomous agents:

```mermaid
flowchart LR
    A[Telemetry Data] --> B[1. Insight Agent]
    B --> C[2. Decision Agent]
    C --> D[3. Campaign & Pricing Agent]
    D --> E[4. Guardrail & Orchestrator]
    E -->|1-Click Approval| F[Razorpay Rails]
    F -->|Webhook: payment.captured| G[5. Experiment Agent]
    G -->|Statistical Lift Feedback| C
```

### 1. Insight Agent (`insight_agent.py`)
- Analyzes cart events, browsing sessions, and order items.
- Identifies funnel anomalies (e.g., product pairing abandonment, high churn propensity > 0.70).
- Emits structured `insights` with empirical evidence.

### 2. Growth Decision Agent (`decision_agent.py`)
- Transforms raw insights into quantifiable commercial `opportunities`.
- Computes **Priority Score = Expected Revenue Impact × Confidence × Urgency Factor**.
- Ranks plays mathematically and sets up hypothesis testing parameters.

### 3. Campaign & Pricing Agent (`campaign_agent.py`)
- Determines targeted customer segment and optimal product offering.
- Formulates **Deterministic Dynamic Discount Bands** using base price, product gross margin, and stock velocity.
- Auto-generates personalized marketing copy tailored to customer segments (e.g., churn recovery, VIP bundle).

### 4. Guardrail & Orchestrator Agent (`orchestrator.py` & `guardrails.py`)
- Classifies proposals into risk tiers:
  - **Low Risk**: <= 5% discount, <= 500 audience → Auto-executable or 1-click approval.
  - **Medium Risk**: <= 10% discount, <= 1,000 audience → Mandatory 1-click human gate.
  - **High Risk**: > 10% discount or > 1,000 audience → Mandatory written justification required.
  - **Blocked**: Exceeds dynamic margin ceiling → Rejected immediately.
- Dispatches authenticated **Razorpay Test Orders** and **Payment Links**.

### 5. Experiment Agent (`experiment_agent.py`)
- Continuously observes post-campaign conversion data.
- Runs a **two-proportion Z-test** against pre-campaign baseline conversion.
- Updates future model confidence (+0.05 on validated success, -0.08 on payment failures).

---

## 📐 Mathematical Rigor & Zero Hallucination

> **Architectural Principle:** LLMs draft creative copy, but **all financial, pricing, and risk decisions are governed by deterministic mathematics**. No LLM can hallucinate discounts or erode unit margins.

### 1. Churn Propensity Scoring
$$\text{Recency Factor} = \min\left(1.0, \frac{\text{Days Since Last Order}}{120}\right)$$
$$\text{Session Factor} = \min\left(1.0, \frac{\text{Days Since Last Session}}{90}\right)$$
$$\text{Frequency Factor} = \min\left(1.0, \max\left(0, 1.0 - \frac{\text{Total Orders}}{10}\right)\right)$$
$$\mathbf{\text{Churn Score} = 0.50 \times \text{Recency} + 0.30 \times \text{Session} + 0.20 \times \text{Frequency}}$$
*(A customer with a score > 0.70 is flagged as High Churn Risk).*

### 2. Opportunity Priority Scoring
$$\mathbf{\text{Priority Score} = \text{Expected Revenue Impact (₹)} \times \text{Confidence} \times \text{Urgency Factor}}$$
*Example (Tenant A - Earbud Stand Recovery):*  
$₹81,600 \times 0.78 \times 1.25 = \mathbf{79,560.00}$ (Ranked #1 Growth Play).

### 3. Deterministic Dynamic Discount Band
$$\text{Base Max Discount} = \text{Product Margin \%} \times 0.25$$
$$\text{Max Allowed Discount} = \min(25.0\%, \max(5.0\%, \text{Base Max} \times \text{Inventory Urgency}))$$
$$\text{Min Incentive Discount} = \max(2.0\%, \min(5.0\%, \text{Product Margin \%} \times 0.08))$$
*Example (Earbud Stand with 50% Margin & 1.3 Urgency Factor):*  
Band = **[3.0%, 12.0%]**, Recommended = **8.0%** (₹1,104 offer price).

### 4. Two-Proportion Hypothesis Z-Test
$$p_{\text{pool}} = \frac{p_{\text{baseline}} + p_{\text{actual}}}{2}$$
$$SE = \sqrt{p_{\text{pool}} (1 - p_{\text{pool}}) \left(\frac{2}{n}\right)}$$
$$Z = \frac{p_{\text{actual}} - p_{\text{baseline}}}{SE}$$
*Example:* Baseline $p = 6.0\%$, Post-Campaign $p = 12.5\%$, sample $n = 850$:  
**$Z = 4.62 \implies p < 0.0001$** (Statistically proven revenue lift at >99.9% confidence).

---

## 🔒 Multi-Tenant Architecture & Security

GrowthPilot supports enterprise multi-tenancy with strict logical and physical data isolation.

### Pre-Configured Demo Tenants
1. **Tenant A: SoundWave Audio (`tenant_store_alpha`)**
   - Premium consumer electronics & audio accessories (Earbud Pro, Charging Stands).
   - High-margin catalog, checkout recovery opportunities.
2. **Tenant B: PulseWear Smart Gear (`tenant_store_beta`)**
   - Performance wearables & fitness trackers (FitPulse Pro, Recovery Bands).
   - Volume-oriented catalog, VIP churn reactivation opportunities.

### Security Guarantees
- **No Client Spoofing:** `tenant_id` is never trusted from query parameters or request bodies. The FastAPI gateway extracts it strictly from the server-verified JWT claims via `get_current_tenant`.
- **Cross-Tenant Data Isolation:** A tenant cannot read, approve, or execute campaigns belonging to another tenant (returns `404 Not Found` / `403 Forbidden`).
- **Postgres Row Level Security (RLS):**
  ```sql
  ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
  CREATE POLICY tenant_isolation_policy ON customers
      USING (tenant_id = current_setting('app.current_tenant', true));
  ```
- **PCI-DSS Compliant Audit Trail:** Payloads logged in `audit_logs` are scrubbed of card numbers, CVVs, and API secrets. Every record is stored alongside a cryptographic **SHA-256 payload hash** for non-repudiation.
- **Sliding-Window Rate Limiting:** Enforced independently per tenant using Redis keys (`rate_limit:{tenant_id}:{route}:{minute}`).

---

## 💳 Live Razorpay Rails & Event Loop

GrowthPilot integrates deeply with Razorpay test-mode rails to execute and monitor commerce plays end-to-end.

![Razorpay Event Flow](docs/razorpay_event_flow.png)

1. **Order & Payment Link Generation:** Upon campaign approval, the Orchestrator generates a test-mode Razorpay Order and short URL Payment Link (`rzp.io/i/plink_xxx`).
2. **Cryptographic HMAC-SHA256 Webhook Verification:** Incoming webhooks from Razorpay are verified against the raw payload bytes using constant-time `hmac.compare_digest`.
3. **Non-Blocking Asynchronous Redis Queue:** Webhooks return `200 OK` in < 5 ms, enqueuing the event into `growthpilot:events:queue`.
4. **Background Event Worker:** An asynchronous background worker pops events from Redis, updates execution states, invalidates cached queries, and triggers re-analysis.
5. **Payment Failure Intelligence:** When `payment.failed` is received, GrowthPilot applies an automated **-0.08 confidence penalty** to the opportunity, stopping money from being spent on failing campaign types.

---

## 🗄️ Database Schema (12 Relational Tables)

The storage layer supports **Supabase PostgreSQL** with automated Alembic migrations and a zero-configuration local **SQLite WAL** fallback.

![Database ER Diagram](docs/er_diagram.png)

| Table | Description |
|---|---|
| `customers` | Customer profiles, demographic segments, acquisition channels, tenant mapping. |
| `products` | Product catalog, base prices, gross margin %, inventory counts, urgency factors. |
| `order_items` | Granular purchase history, items, quantities, historical discounts, line-item revenue. |
| `sessions` | Web browsing sessions, durations, acquisition channels. |
| `cart_events` | Granular funnel actions: product views, cart additions, checkout drop-offs. |
| `insights` | Telemetry anomalies detected by the Insight Agent. |
| `opportunities` | Prioritized growth plays scored by Impact × Confidence × Urgency. |
| `campaign_proposals` | Drafted growth campaigns, target segments, dynamic discount bands, marketing copy. |
| `campaign_interactions` | Post-campaign customer engagements, opens, clicks, checkouts. |
| `executions` | Realized executions linked to Razorpay Order IDs and Payment Link IDs. |
| `experiment_results` | Two-proportion Z-test statistical results, hypothesis verdicts, AI reasoning. |
| `audit_logs` | Immutable audit log with sanitized payloads and SHA-256 hashes. |

---

## 🖥️ Single-Page Interactive Dashboard

The dashboard (`frontend/index.html`) is a responsive single-page application built with clean semantic HTML, modern styling, and Chart.js:

1. **Executive Overview:** Live GMV, revenue, average order value, cart abandonment rate, and 30-day revenue trends.
2. **Opportunities Explorer:** Ranked opportunity table displaying expected revenue lift, priority score, and 1-click campaign generation.
3. **Campaign Studio & Guardrails:** Visual discount band sliders, risk tier badges (Low / Med / High / Blocked), approval modals, and instant Razorpay payment link launcher.
4. **Experiment Analytics:** Pre vs post campaign conversion bar charts, Z-scores, p-values, and statistical hypothesis verdicts.
5. **Audit Trail Inspector:** Real-time log of agent actions, webhook deliveries, and SHA-256 payload verification hashes.
6. **1-Click Tenant Switcher:** Switch between **SoundWave Audio (Tenant A)** and **PulseWear (Tenant B)** with instantaneous UI re-hydration.

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.10+
- (Optional) Docker or local Redis & Supabase account. If omitted, GrowthPilot automatically falls back to **in-memory Fakeredis** and **SQLite WAL mode**.

### 1. Clone & Setup Environment
```bash
git clone https://github.com/[your-username]/Growth_pilot.git
cd Growth_pilot

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key variables in `.env`:
```ini
# Database: Supabase Postgres URL (or omit to use local SQLite)
DATABASE_URL=postgresql://postgres.xxx:xxx@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require

# Redis: Cloud or local Redis (or omit for automatic in-memory fallback)
REDIS_URL=redis://localhost:6379/0

# Razorpay: Test-Mode credentials
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Multi-Tenant default
DEMO_TENANT_ID=tenant_store_alpha
```

### 3. One-Click Launcher
Run the automated launcher:
```bash
python run_growthpilot.py
```
This script automatically:
1. Seeds 6 months of realistic synthetic e-commerce telemetry for both demo tenants.
2. Runs the multi-agent pipeline to generate fresh insights and ranked opportunities.
3. Starts the FastAPI server and background Redis event consumer.

- **Web Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📡 Complete API Reference

All REST endpoints require a verified Supabase JWT Bearer token, except for auth and webhook endpoints.

| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `POST` | `/api/auth/login` | Authenticate with email + password, returns JWT with `tenant_id` | — |
| `POST` | `/api/auth/demo-login` | 1-Click login for Tenant Alpha (`SoundWave`) or Beta (`PulseWear`) | — |
| `POST` | `/api/auth/signup` | Register new store tenant account | — |
| `GET` | `/api/auth/me` | Current authenticated user profile & tenant context | — |
| `GET` | `/api/overview` | Core business KPIs & charts (Redis cached 45s) | — |
| `GET` | `/api/customers/segments` | RFM customer segmentation breakdown for tenant | — |
| `GET` | `/api/customers/churn-risk` | High-churn-risk customer list (churn score > 0.70) | — |
| `GET` | `/api/products/trends` | 30-day product velocity and inventory health | — |
| `GET` | `/api/opportunities` | Ranked commercial opportunities (Redis cached 60s) | — |
| `GET` | `/api/opportunities/{id}` | Detailed parameters for a single opportunity | — |
| `POST` | `/api/opportunities/{id}/campaign` | Run Campaign Agent to draft proposal & dynamic discount band | — |
| `GET` | `/api/campaigns/{id}` | Retrieve campaign proposal details & guardrail risk tier | — |
| `POST` | `/api/campaigns/{id}/approve` | Human approval gate; generates Razorpay Order & Payment Link | 15 req/min |
| `POST` | `/api/campaigns/{id}/execute` | Dispatch campaign to execution rails | 15 req/min |
| `GET` | `/api/experiments/{id}` | Two-proportion Z-test statistical results & hypothesis verdict | — |
| `GET` | `/api/audit-log` | Tamper-evident audit trail with SHA-256 payload hashes | — |
| `POST` | `/api/pipeline/run` | Re-run full 5-agent multi-agent analysis for current tenant | — |
| `POST` | `/api/webhooks/razorpay` | **Razorpay Webhook Listener** (HMAC-SHA256 verified, Redis queue) | 30 req/min |
| `POST` | `/api/razorpay/simulate-webhook` | Developer testing helper to simulate signed Razorpay webhooks | — |

---

## 🧪 Testing & Validation

GrowthPilot includes a comprehensive automated test suite covering unit economics, agent orchestration, multi-tenancy, rate limiting, and payment flows.

```bash
python -m pytest tests/ -v
```

### Test Coverage Highlights (28 / 28 Passed ✅)
- `tests/test_growthpilot.py`: RFM segmentation, churn propensity scoring, linear trend regression, priority formulas, risk tier classification, and agent orchestration.
- `tests/test_phase2_postgres_redis.py`: Multi-tenant schema validation, SQLAlchemy sessions, dynamic discount band protection, Razorpay order/payment link creation, HMAC-SHA256 signature verification, `payment.failed` penalty degradation, Redis queueing, and Redis 45s caching.
- `tests/test_phase3_multi_tenant_auth.py`: JWT verification, cross-tenant isolation enforcement (Tenant B blocked from Tenant A resources), second tenant independent dataset verification, and per-tenant rate limiter isolation.
- `tests/test_razorpay.py`: Live and test-mode Razorpay SDK transactions and webhook ingestion.

---

## 📁 Directory Structure

```
Growth_pilot/
├── backend/
│   └── app/
│       ├── agents/                  # 5-Agent Multi-Agent Core
│       │   ├── insight_agent.py     # Funnel anomaly & churn detection
│       │   ├── decision_agent.py    # Opportunity scoring & prioritization
│       │   ├── campaign_agent.py    # Dynamic pricing & copy generation
│       │   ├── orchestrator.py      # State machine coordinator & Razorpay dispatch
│       │   └── experiment_agent.py  # Two-proportion Z-test statistical evaluator
│       ├── api/
│       │   └── routes.py            # 18 REST endpoints (Auth, Analytics, Webhooks)
│       ├── auth/
│       │   ├── jwt_auth.py          # PyJWT token engine & password verification
│       │   └── dependencies.py      # Server-side get_current_tenant extractor
│       ├── db/
│       │   ├── models.py            # SQLite/Postgres schema & sanitized audit log
│       │   ├── database.py          # SQLAlchemy dual engine & Supabase RLS
│       │   └── seed_synthetic_data.py # 6-month synthetic multi-tenant dataset
│       ├── integrations/
│       │   ├── redis_client.py      # Redis queue, worker loop & query cache
│       │   └── rate_limiter.py      # Sliding-window per-tenant rate limiter
│       ├── tools/
│       │   ├── razorpay.py          # Razorpay Orders, Links, Webhooks & Penalties
│       │   ├── guardrails.py        # Margin-safe dynamic discount bands
│       │   ├── scoring.py           # Priority scoring formulas
│       │   ├── churn.py             # Vectorized churn propensity model
│       │   ├── segmentation.py      # Vectorized RFM customer segmentation
│       │   └── trend.py             # Product inventory & velocity analytics
│       └── main.py                  # FastAPI application entrypoint
├── docs/                            # Architectural diagrams & PDF documentation
│   ├── architecture_diagram.png
│   ├── er_diagram.png
│   ├── razorpay_event_flow.png
│   ├── generate_diagrams.py
│   └── generate_viva_pdf.py
├── frontend/                        # Responsive Single-Page Application
│   ├── index.html                   # Multi-view dashboard & Chart.js visualizer
│   └── login.html                   # Auth & 1-click store switcher
├── tests/                           # Complete test suite (28 test cases)
│   ├── conftest.py                  # Pytest bootstrap with offline fallbacks
│   ├── test_growthpilot.py
│   ├── test_phase2_postgres_redis.py
│   ├── test_phase3_multi_tenant_auth.py
│   └── test_razorpay.py
├── data/                            # Local database storage (growthpilot.db)
├── run_growthpilot.py               # 1-Click CLI launcher
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
└── README.md                        # Master documentation
```

---

## 🏆 Key Innovations & Architectural Highlights

1. **Closed-Loop Commerce:** From finding an abandoned cart to issuing a Razorpay checkout link and tracking statistical conversion, without human context switching.
2. **Deterministic Financial Guardrails:** Mathematical dynamic discount ceiling eliminates AI hallucination and protects merchant unit economics.
3. **Resilient Dual-Mode Engineering:** Production-ready with Supabase Postgres and Redis, yet runs 100% offline with zero cloud configuration via SQLite WAL and Fakeredis.
4. **Autonomous Degradation on Payment Failure:** Automated -0.08 confidence penalty prevents the system from blindly repeating campaigns that fail at checkout.
5. **PCI-DSS Compliant Tamper-Evident Trail:** Immutable audit logs with sensitive fields redacted and SHA-256 hashes verifying system integrity.
