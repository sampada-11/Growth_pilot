"""
Script to generate GrowthPilot_Viva_Interview_Guide.pdf
Uses ReportLab to produce an executive-ready, highly detailed PDF covering all 12 interview/viva topics.
"""
import os
import sys
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas that enables two-pass page numbering ('Page X of Y')."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 805, "GrowthPilot (AI Commerce Growth Agent) — Comprehensive Technical & Viva Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(40, 798, 555, 798)

        # Running Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 42, 555, 42)
        
        self.drawString(40, 30, "CONFIDENTIAL & PROPRIETARY — PREPARED FOR INTERVIEW & TECHNICAL VIVA")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(555, 30, page_str)
        self.restoreState()


def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    primary_color = colors.HexColor("#0f172a") # Slate 900
    accent_color = colors.HexColor("#0284c7")  # Sky 600
    subtext_color = colors.HexColor("#475569") # Slate 600
    card_bg = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#e2e8f0")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.white,
        alignment=0,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#93c5fd"),
        alignment=0,
        spaceAfter=12
    )

    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#cbd5e1"),
        alignment=0
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=accent_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    formula_style = ParagraphStyle(
        'Formula_Custom',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0369a1"),
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.5,
        textColor=colors.HexColor("#334155")
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor("#1e293b")
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=primary_color
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.2,
        leading=11,
        textColor=colors.white
    )

    story = []

    # ─────────────────────────────────────────────────────────────
    # TITLE BANNER
    # ─────────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph("GROWTHPILOT: AUTONOMOUS AI COMMERCE SYSTEM", title_style),
        ],
        [
            Paragraph("Complete Project Architecture, Engineering Principles & Technical Viva Master Guide", subtitle_style),
        ],
        [
            Paragraph("<b>Stack:</b> FastAPI · Supabase PostgreSQL (RLS) · SQLite Fallback · Redis Event Queue & Cache · Razorpay API & Webhooks · Multi-Agent AI Core", tagline_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[515])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('CORNERPAD', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────────
    # 1. OBJECTIVE & PROBLEM STATEMENT
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("1. Project Objective & Problem Statement", h1_style))
    story.append(Paragraph(
        "<b>The Fundamental Problem:</b> E-commerce stores capture huge amounts of behavioral telemetry (clicks, sessions, cart add/abandon events, orders), yet store owners face the <b>'Analytics-to-Action Gap'</b>. Dashboards tell merchants what failed in the past (e.g., <i>'Cart abandonment surged to 71% on Earbud Stands'</i>), but do not tell them what commercial play to run next. Manually calculating unit margins, remaining inventory, customer lifetime value (CLV), drafting marketing copy, and setting up payment links takes hours and carries high human risk of margin cannibalization.",
        body_style
    ))
    story.append(Paragraph(
        "<b>GrowthPilot Core Mission:</b> <i>'Your business's AI growth team — it finds the opportunity, decides the play, and runs it.'</i><br/>"
        "GrowthPilot closes this gap as an autonomous multi-agent software system that: (1) ingests behavioral telemetry, (2) extracts growth bottlenecks, (3) mathematically prioritizes opportunities, (4) calculates dynamic discount bands protecting unit economics, (5) gates execution through human-in-the-loop approval, (6) generates live Razorpay payment links, and (7) statistically validates outcomes via two-proportion Z-tests in a closed feedback loop.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # ─────────────────────────────────────────────────────────────
    # 2. OVERALL ARCHITECTURE & WORKFLOW
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("2. Overall Architecture & Workflow", h1_style))
    story.append(Paragraph(
        "GrowthPilot utilizes a robust <b>4-Tier Enterprise Architecture</b> ensuring multi-tenant isolation, real-time caching, resilient webhook ingestion, and mathematical guardrails:",
        body_style
    ))

    arch_img_path = os.path.join(os.path.dirname(__file__), "architecture_diagram.png")
    if os.path.exists(arch_img_path):
        story.append(Image(arch_img_path, width=515, height=294))
        story.append(Spacer(1, 6))

    story.append(Paragraph(
        "• <b>Tier 1 (Client & Auth):</b> Single-Page HTML5 Dashboard (Tailwind CSS, Chart.js) authenticating via Supabase JWT Bearer tokens with 1-click store tenant context switching.<br/>"
        "• <b>Tier 2 (FastAPI Gateway):</b> Protected by strict server-side tenant derivation (<code>get_current_tenant</code>), per-tenant sliding window Redis rate limiting, and 30-60s Redis caching.<br/>"
        "• <b>Tier 3 (5-Agent AI Core):</b> Insight Agent &rarr; Growth Decision Agent &rarr; Campaign & Pricing Agent &rarr; Orchestrator & Guardrails &rarr; Experiment Agent.<br/>"
        "• <b>Tier 4 (Persistence & Event Bus):</b> Supabase Postgres with Row Level Security (RLS) policies + zero-ops SQLite fallback, Redis queue <code>growthpilot:events:queue</code> with an asynchronous worker thread, and Razorpay test-mode execution.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # ─────────────────────────────────────────────────────────────
    # 3. TECHNOLOGIES, FRAMEWORKS & APIS
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("3. Technologies, Frameworks, APIs & Selection Rationale", h1_style))
    
    tech_data = [
        [Paragraph("Technology", table_header), Paragraph("Role in GrowthPilot", table_header), Paragraph("Architectural Rationale / Why Chosen", table_header)],
        [
            Paragraph("<b>FastAPI</b>", table_cell_bold),
            Paragraph("REST Gateway & Webhook listener", table_cell),
            Paragraph("Async request throughput, native Pydantic validation, dependency injection for verified auth, automatic Swagger docs.", table_cell)
        ],
        [
            Paragraph("<b>Supabase Postgres</b>", table_cell_bold),
            Paragraph("Primary multi-tenant relational DB", table_cell),
            Paragraph("Native PostgreSQL Row Level Security (RLS) policies enforce physical data isolation across tenants at the engine level.", table_cell)
        ],
        [
            Paragraph("<b>SQLite (WAL Mode)</b>", table_cell_bold),
            Paragraph("Zero-ops offline/local fallback", table_cell),
            Paragraph("Zero cloud dependencies needed for local developer runs and CI testing; WAL mode prevents database locking during concurrent writes.", table_cell)
        ],
        [
            Paragraph("<b>Redis & Fakeredis</b>", table_cell_bold),
            Paragraph("Event queue, cache & rate limiter", table_cell),
            Paragraph("Sub-millisecond latency for webhook burst ingestion (`growthpilot:events:queue`), 45s query caching, and rate limiting; Fakeredis allows seamless offline tests.", table_cell)
        ],
        [
            Paragraph("<b>Razorpay API</b>", table_cell_bold),
            Paragraph("Payment Orders, Links & Webhooks", table_cell),
            Paragraph("Industry-standard payment rails in India. Enables automated Test Orders, dynamic SMS/Email Payment Links, and HMAC-SHA256 webhooks.", table_cell)
        ],
        [
            Paragraph("<b>Pandas & NumPy</b>", table_cell_bold),
            Paragraph("Vectorized telemetry analytics", table_cell),
            Paragraph("Calculates RFM segmentation, churn propensity models, linear trend regression, and statistical Z-tests in milliseconds without latency.", table_cell)
        ],
        [
            Paragraph("<b>PyJWT & HMAC</b>", table_cell_bold),
            Paragraph("Security & cryptographic validation", table_cell),
            Paragraph("Cryptographic JWT tenant claims verification, constant-time password verification, and tamper-evident SHA-256 webhook payload hashing.", table_cell)
        ],
    ]
    tech_table = Table(tech_data, colWidths=[105, 140, 270])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────────
    # 4. EVERY MAJOR FEATURE & MODULE
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("4. Major Features & Module Deep-Dive", h1_style))
    story.append(Paragraph(
        "<b>1. Multi-Tenant Isolation & Store Switcher:</b> All business tables contain a <code>tenant_id</code> column. Two complete demo businesses are provided: (a) <i>Tenant A (SoundWave Audio)</i> featuring high-end consumer audio, and (b) <i>Tenant B (PulseWear Smart Gear)</i> featuring fitness wearables. Tenant identity is extracted server-side strictly from the verified JWT bearer token.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2. Five Autonomous AI Agents:</b><br/>"
        "• <i>Insight Agent:</i> Detects funnel anomalies (e.g. cart abandonment > 70%) and high churn risk.<br/>"
        "• <i>Growth Decision Agent:</i> Quantifies Expected Impact (₹), Confidence (0-1), and Urgency, computing a mathematically ranked Priority Score.<br/>"
        "• <i>Campaign & Pricing Agent:</i> Derives a Dynamic Discount Band from product margin and stock velocity, calculates expected ROI, and drafts marketing copy.<br/>"
        "• <i>Guardrail & Orchestrator Agent:</i> Classifies proposals into Low, Medium, High, or Blocked risk tiers, halts for human approval, and invokes Razorpay API.<br/>"
        "• <i>Experiment Agent:</i> Ingests post-campaign conversion, runs two-proportion Z-tests, and updates future decision confidence (+0.05 on success).",
        body_style
    ))
    story.append(Paragraph(
        "<b>3. Redis Event Queue & Async Worker:</b> Razorpay webhooks (<code>payment.captured</code>, <code>payment.failed</code>) return immediate 200 OK after signature verification and are enqueued to <code>growthpilot:events:queue</code>. A background thread processes events, triggers agent re-analysis, and invalidates stale Redis cache.",
        body_style
    ))
    story.append(Paragraph(
        "<b>4. Payment Failure Degradation Penalty:</b> When a <code>payment.failed</code> webhook arrives, GrowthPilot logs the error, records cart abandonment, and applies an automated <b>-0.08 confidence penalty</b> to open opportunities, preventing repeated execution of failing offers.",
        body_style
    ))
    story.append(Paragraph(
        "<b>5. Per-Tenant Rate Limiting & Tamper-Evident Audit Trail:</b> Sliding window rate limiting prevents API exhaustion (15 approvals/min, 30 webhooks/min). The <code>audit_logs</code> table records every agent action with sanitized payloads (PCI-DSS compliant, all card/secret keys redacted) and SHA-256 payload hashes.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────────
    # 5. DATABASE, BACKEND & FRONTEND FLOW
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("5. Database, Backend & Frontend Flow", h1_style))
    story.append(Paragraph(
        "The relational schema comprises <b>12 core tables</b> scoped by <code>tenant_id</code> and secured via Row Level Security (RLS) policies:",
        body_style
    ))

    er_img_path = os.path.join(os.path.dirname(__file__), "er_diagram.png")
    if os.path.exists(er_img_path):
        story.append(Image(er_img_path, width=515, height=331))
        story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Data Lifecycle:</b> Raw Telemetry &rarr; (<code>customers</code>, <code>products</code>, <code>sessions</code>, <code>cart_events</code>, <code>order_items</code>) &rarr; Analytics Tools &rarr; <code>insights</code> &rarr; Scoring &rarr; <code>opportunities</code> &rarr; Strategy &rarr; <code>campaign_proposals</code> &rarr; Human Approval &rarr; <code>executions</code> &rarr; Post-Campaign Evaluation &rarr; <code>experiment_results</code>.<br/>"
        "<b>Supabase RLS Policy:</b> <code>USING (tenant_id = current_setting('app.current_tenant', true))</code>. Every SQLAlchemy session sets this configuration parameter upon connection checkout, preventing any possibility of cross-tenant data leakage.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────────
    # 6. AI/ML LOGIC & MATHEMATICAL FORMULAS
    # ─────────────────────────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("6. AI/ML Components, Logic & Mathematical Formulas", h1_style),
        Paragraph(
            "GrowthPilot uses transparent, deterministic mathematical and statistical models for all financial decisions to eliminate LLM hallucination and protect commercial margins:",
            body_style
        ),
        Paragraph("<b>A. Churn Propensity Score (churn.py):</b>", h2_style),
        Paragraph("Recency Factor = min(1.0, Days Since Last Order / 120)<br/>"
                  "Session Factor = min(1.0, Days Since Last Session / 90)<br/>"
                  "Frequency Factor = min(1.0, max(0, 1.0 - (Total Orders / 10)))<br/>"
                  "<b>Churn Score = 0.50 × Recency + 0.30 × Session + 0.20 × Frequency</b> (High risk if > 0.70)", formula_style),
        
        Paragraph("<b>B. Opportunity Priority Scoring (scoring.py):</b>", h2_style),
        Paragraph("<b>Priority Score = Expected Revenue Impact × Confidence × Urgency Factor</b><br/>"
                  "<i>Tenant A Example:</i> ₹81,600 × 0.78 × 1.25 = <b>79,560.00</b> (Ranked #1)", formula_style),

        Paragraph("<b>C. Deterministic Dynamic Discount Band (guardrails.py):</b>", h2_style),
        Paragraph("Base Max Discount = Product Margin % × 0.25 (Never sacrifice unit economics)<br/>"
                  "Max Allowed Discount = min(25.0, max(5.0, Base Max × Inventory Urgency Factor))<br/>"
                  "Min Incentive Discount = max(2.0, min(5.0, Product Margin % × 0.08))<br/>"
                  "<i>Earbud Stand (50% Margin, 1.3 Urgency):</i> Band = [3.0%, 12.0%], Recommended = <b>8.0%</b>", formula_style),

        Paragraph("<b>D. Statistical Significance Two-Proportion Z-Test (experiment_agent.py):</b>", h2_style),
        Paragraph("p_pool = (p_baseline + p_actual) / 2 = (0.06 + 0.125) / 2 = 0.0925<br/>"
                  "SE = sqrt( p_pool × (1 - p_pool) × (2 / n) ) = sqrt( 0.0925 × 0.9075 × (2 / 850) ) = 0.01406<br/>"
                  "<b>Z = (p_actual - p_baseline) / SE = (0.125 - 0.06) / 0.01406 = 4.62 &rarr; p < 0.0001</b> (Statistically Significant at >99% confidence)", formula_style),
        Spacer(1, 6)
    ]))

    # ─────────────────────────────────────────────────────────────
    # 7. IMPORTANT FILES & WHAT EACH DOES
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("7. Important Files & Architectural Directory Structure", h1_style))

    file_data = [
        [Paragraph("File Path", table_header), Paragraph("Layer", table_header), Paragraph("Functional Responsibility", table_header)],
        [Paragraph("backend/app/main.py", table_cell_bold), Paragraph("Server Entry", table_cell), Paragraph("Initializes DB, seeds demo data, starts Redis background worker, mounts APIs & static dashboard.", table_cell)],
        [Paragraph("run_growthpilot.py", table_cell_bold), Paragraph("CLI Launcher", table_cell), Paragraph("One-click script that executes migrations, seeds synthetic dataset, runs pipeline, and starts Uvicorn.", table_cell)],
        [Paragraph("backend/app/api/routes.py", table_cell_bold), Paragraph("FastAPI Routes", table_cell), Paragraph("All 18 endpoints: Auth, Overview, Segments, Churn, Trends, Opportunities, Campaigns, Razorpay Webhook.", table_cell)],
        [Paragraph("backend/app/auth/dependencies.py", table_cell_bold), Paragraph("Security", table_cell), Paragraph("Enforces Bearer JWT verification and extracts tenant_id strictly server-side (`get_current_tenant`).", table_cell)],
        [Paragraph("backend/app/auth/jwt_auth.py", table_cell_bold), Paragraph("Auth Engine", table_cell), Paragraph("Handles JWT generation, HS256 signature verification, password hashing, and pre-registered demo accounts.", table_cell)],
        [Paragraph("backend/app/db/models.py", table_cell_bold), Paragraph("Schema / Audit", table_cell), Paragraph("SQLite/Postgres schema, thread-safe connection pooling (WAL mode), and sanitized `log_audit()` engine.", table_cell)],
        [Paragraph("backend/app/db/database.py", table_cell_bold), Paragraph("ORM / RLS", table_cell), Paragraph("SQLAlchemy engine supporting dual-mode (Supabase Postgres + SQLite fallback) and `setup_supabase_rls()`.", table_cell)],
        [Paragraph("backend/app/agents/orchestrator.py", table_cell_bold), Paragraph("Orchestration", table_cell), Paragraph("Coordinates 5-agent pipeline, enforces human approval gating, and dispatches Razorpay orders/links.", table_cell)],
        [Paragraph("backend/app/tools/razorpay.py", table_cell_bold), Paragraph("Payment Gateway", table_cell), Paragraph("Razorpay Orders & Payment Links, HMAC-SHA256 signature verification, and -0.08 payment failure penalty.", table_cell)],
        [Paragraph("backend/app/tools/guardrails.py", table_cell_bold), Paragraph("Safety Logic", table_cell), Paragraph("Computes unit-margin dynamic discount bands and categorizes proposals into Low/Med/High/Blocked tiers.", table_cell)],
        [Paragraph("backend/app/integrations/redis_client.py", table_cell_bold), Paragraph("Queue & Cache", table_cell), Paragraph("Redis event queue, background worker thread loop, 45s TTL query caching, and dynamic invalidation.", table_cell)],
        [Paragraph("frontend/index.html", table_cell_bold), Paragraph("Dashboard UI", table_cell), Paragraph("Single-page responsive dashboard with 6 views, Chart.js graphs, and 1-click store switcher.", table_cell)],
    ]
    file_table = Table(file_data, colWidths=[150, 85, 280])
    file_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    story.append(file_table)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────────
    # 8. END-TO-END USER FLOW WITH CONCRETE EXAMPLE
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("8. End-to-End User Flow (Concrete Walkthrough: SoundWave Audio)", h1_style))
    story.append(Paragraph(
        "<b>Step 1 — Auth & Context:</b> Growth manager selects <i>'SoundWave Audio (Tenant A)'</i>. The client logs in via <code>POST /api/auth/demo-login {tenant: 'alpha'}</code>. A cryptographically signed JWT containing <code>tenant_store_alpha</code> is returned.<br/>"
        "<b>Step 2 — Bottleneck Detection:</b> Insight Agent identifies that 850 Earbud Pro buyers frequently add Earbud Stand (PROD-002) to cart, but 71% abandon checkout (conversion bottlenecked at 6.0%).<br/>"
        "<b>Step 3 — Priority Scoring:</b> Growth Decision Agent scores the opportunity: ₹81,600 Expected Lift × 0.78 Confidence × 1.25 Urgency = <b>79,560 Priority Score</b> (Ranked #1).<br/>"
        "<b>Step 4 — Strategy & Guardrails:</b> Campaign Agent inspects PROD-002 (₹1,200 base price, 50% margin, 1.3 inventory urgency). Formula yields dynamic band [3%, 12%]. Proposes <b>8.0% discount</b> (₹1,104 offer price). Guardrail categorizes as <b>Medium Risk</b> (<=10% discount, <=1,000 customers &rarr; 1-click human approval).<br/>"
        "<b>Step 5 — Approval & Execution:</b> Manager clicks <i>'Approve & Execute'</i>. Orchestrator calls Razorpay API to generate live Test-Mode Order and Payment Link (<code>rzp.io/i/plink_test_xxx</code>), generating an execution token.<br/>"
        "<b>Step 6 — Razorpay Webhook & Closed-Loop:</b> Customer pays. Razorpay issues <code>payment.captured</code> webhook. FastAPI verifies HMAC-SHA256 signature, hashes payload, and pushes event into Redis. The background worker consumes the event, triggers Experiment Agent (conversion rose 6% &rarr; 12.5%, Z=4.62, p<0.0001), records ₹71,400 realized revenue, and boosts future decision confidence by +0.05.",
        body_style
    ))

    rzp_img_path = os.path.join(os.path.dirname(__file__), "razorpay_event_flow.png")
    if os.path.exists(rzp_img_path):
        story.append(Image(rzp_img_path, width=515, height=202))
        story.append(Spacer(1, 6))

    # ─────────────────────────────────────────────────────────────
    # 9. KEY TECHNICAL DECISIONS & ALTERNATIVES
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("9. Key Technical Decisions & Alternatives Considered", h1_style))

    dec_data = [
        [Paragraph("Decision Area", table_header), Paragraph("Chosen Approach", table_header), Paragraph("Rejected Alternative", table_header), Paragraph("Engineering Rationale", table_header)],
        [
            Paragraph("<b>Pricing & Guardrails</b>", table_cell_bold),
            Paragraph("Deterministic mathematical formulas", table_cell),
            Paragraph("Autonomous LLM prompting", table_cell),
            Paragraph("LLMs hallucinate arithmetic and unit costs. Deterministic math guarantees margins are never breached.", table_cell)
        ],
        [
            Paragraph("<b>Persistence</b>", table_cell_bold),
            Paragraph("Dual-Engine: Supabase Postgres + SQLite WAL", table_cell),
            Paragraph("Postgres-only or SQLite-only", table_cell),
            Paragraph("Gives zero-ops local execution for testing, while maintaining enterprise RLS capabilities in cloud production.", table_cell)
        ],
        [
            Paragraph("<b>Webhook Transport</b>", table_cell_bold),
            Paragraph("Redis Queue + Background Worker Thread", table_cell),
            Paragraph("Synchronous inline webhook processing", table_cell),
            Paragraph("Prevents webhook gateway HTTP timeouts and isolates backend pipeline re-runs from traffic spikes.", table_cell)
        ],
        [
            Paragraph("<b>Tenant Auth</b>", table_cell_bold),
            Paragraph("Server-side JWT claims extraction", table_cell),
            Paragraph("Client request body / query parameter", table_cell),
            Paragraph("Client-supplied tenant identifiers introduce Insecure Direct Object Reference (IDOR) vulnerabilities.", table_cell)
        ],
    ]
    dec_table = Table(dec_data, colWidths=[95, 120, 110, 190])
    dec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    story.append(dec_table)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────────
    # 10. HOW TO RUN, TEST & DEPLOY
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("10. How to Run, Test & Deploy", h1_style))
    story.append(Paragraph(
        "<b>1. Environment Setup:</b> Copy <code>.env.example</code> to <code>.env</code>. Populate Supabase Postgres URL and Razorpay Test credentials (or leave defaults for local zero-ops execution).<br/>"
        "<b>2. Install Dependencies:</b> <code>.\\venv\\Scripts\\pip install -r requirements.txt</code><br/>"
        "<b>3. Run Migrations (Supabase):</b> <code>alembic upgrade head</code><br/>"
        "<b>4. Start Application:</b> <code>.\\venv\\Scripts\\python run_growthpilot.py</code> &rarr; Access dashboard at <b>http://127.0.0.1:8000/</b> and OpenAPI docs at <b>/docs</b>.<br/>"
        "<b>5. Run Test Suite:</b> <code>.\\venv\\Scripts\\python -m pytest tests/ -v</code> (Executes 28 unit & integration tests in ~14 seconds with 100% pass rate).<br/>"
        "<b>6. Production Deployment:</b> Dockerized container deployed to AWS ECS, Render, or Railway; backed by managed Redis (Upstash) and Supabase PostgreSQL with pooler.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────────
    # 11. COMMON ERRORS & HOW TO FIX THEM
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("11. Common Errors, Root Causes & Fixes", h1_style))
    story.append(Paragraph(
        "• <b>Error 1: <code>sqlite3.OperationalError: database is locked</code></b><br/>"
        "  <i>Cause:</i> Concurrent writes from API thread and background worker.<br/>"
        "  <i>Fix:</i> Enabled SQLite WAL mode (<code>PRAGMA journal_mode=WAL;</code>) and configured a 60-second busy timeout in <code>models.py</code>.<br/>"
        "• <b>Error 2: <code>redis.exceptions.ConnectionError: Connection refused</code></b><br/>"
        "  <i>Cause:</i> Local machine has no Redis service listening on port 6379.<br/>"
        "  <i>Fix:</i> Implemented an automated fallback in <code>redis_client.py</code>: if Redis connection fails, it initializes <code>fakeredis</code> or an in-memory dictionary.<br/>"
        "• <b>Error 3: <code>HTTP 400: Razorpay webhook signature verification failed</code></b><br/>"
        "  <i>Cause:</i> JSON payload was decoded or re-serialized prior to HMAC check.<br/>"
        "  <i>Fix:</i> Verifies signature directly against raw bytes (<code>await request.body()</code>) using HMAC-SHA256 and constant-time comparison (<code>hmac.compare_digest</code>).<br/>"
        "• <b>Error 4: <code>HTTP 429: Too Many Requests</code></b><br/>"
        "  <i>Cause:</i> Rate limit quota exceeded (15 approvals/min or 30 webhooks/min).<br/>"
        "  <i>Fix:</i> Working as intended to prevent API exhaustion. Wait for the window reset or adjust thresholds in <code>rate_limiter.py</code>.<br/>"
        "• <b>Error 5: <code>HTTP 404: Opportunity/Campaign not found for tenant</code></b><br/>"
        "  <i>Cause:</i> Cross-tenant access attempt (e.g. Tenant B attempting to read Tenant A's campaign).<br/>"
        "  <i>Fix:</i> Security isolation working as designed. Switch store context via the dashboard header.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────────
    # 12. VIVA & INTERVIEW QUESTIONS WITH SHORT ANSWERS
    # ─────────────────────────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("12. High-Frequency Viva & Technical Interview Questions", h1_style),
        Paragraph("<b>Q1: What fundamentally distinguishes GrowthPilot from a traditional e-commerce dashboard?</b><br/>"
                  "<b>A:</b> Traditional dashboards are passive and descriptive—they show what happened in the past. GrowthPilot is prescriptive and agentic—it autonomously identifies the root-cause bottleneck, calculates margin-safe discounts, requests 1-click human approval, dispatches live payment links via Razorpay, and evaluates statistical lift in a closed feedback loop.", body_style),
        Spacer(1, 4),
        Paragraph("<b>Q2: Why use deterministic algorithms instead of LLM prompting for commercial decisions?</b><br/>"
                  "<b>A:</b> LLMs are non-deterministic and can hallucinate arithmetic, leading to disastrous commercial mistakes such as offering a 40% discount on a 15% margin product. Deterministic algorithms guarantee mathematical unit-margin safety and compliance with financial guardrails.", body_style),
        Spacer(1, 4),
        Paragraph("<b>Q3: How is multi-tenant security enforced to prevent IDOR attacks?</b><br/>"
                  "<b>A:</b> At the application level, <code>tenant_id</code> is never accepted from client request bodies or query parameters; it is extracted strictly from cryptographically verified JWT claims via <code>get_current_tenant</code>. At the database level, PostgreSQL Row Level Security (RLS) policies restrict SQL queries to the active tenant setting.", body_style),
        Spacer(1, 4),
        Paragraph("<b>Q4: Why enqueue Razorpay webhooks into Redis instead of processing them inline?</b><br/>"
                  "<b>A:</b> Payment gateways require an immediate HTTP 200 OK within 2-3 seconds. Processing webhooks synchronously would cause gateway timeouts during burst traffic. Enqueuing to <code>growthpilot:events:queue</code> allows instantaneous non-blocking 200 responses, with background workers processing the workload asynchronously.", body_style),
        Spacer(1, 4),
        Paragraph("<b>Q5: How does the system handle payment failures?</b><br/>"
                  "<b>A:</b> On receiving a <code>payment.failed</code> webhook, the system logs the incident, records the checkout abandonment, and applies an automated -0.08 confidence degradation penalty to open opportunities, preventing the engine from repeating failing offers.", body_style),
        Spacer(1, 4),
        Paragraph("<b>Q6: How does the dynamic discount band formula protect gross profit?</b><br/>"
                  "<b>A:</b> It calculates <code>(min_pct, max_pct, recommended_pct)</code> dynamically by multiplying gross margin by a 25% safety ceiling and scaling by an inventory urgency multiplier. This ensures high-margin surplus inventory can be cleared safely while low-margin items are strictly protected.", body_style),
        Spacer(1, 4),
        Paragraph("<b>Q7: How does the Experiment Agent prove that a campaign succeeded?</b><br/>"
                  "<b>A:</b> It performs a two-proportion Z-test comparing pre-campaign baseline conversion against post-campaign conversion across the cohort. If the resulting Z-score yields p < 0.01, statistical significance is confirmed, triggering an automated +0.05 confidence boost in future decision scoring.", body_style),
        Spacer(1, 4),
        Paragraph("<b>Q8: How does GrowthPilot guarantee PCI-DSS compliance in its audit logs?</b><br/>"
                  "<b>A:</b> The <code>log_audit()</code> function passes all telemetry through a recursive sanitizer that redacts sensitive payment attributes (`card`, `cvv`, `secret`, `password`). Payloads are also hashed with SHA-256 for tamper evidence.", body_style)
    ]))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {output_path}")

if __name__ == "__main__":
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "GrowthPilot_Viva_Interview_Guide.pdf"))
    build_pdf(out)
