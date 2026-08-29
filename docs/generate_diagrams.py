"""
Diagram Generation Script for GrowthPilot Phase 3 Submission
Generates:
1. docs/architecture_diagram.png (5-Agent Architecture + Supabase + Redis + Razorpay)
2. docs/er_diagram.png (Database ER Diagram with multi-tenant tenant_id & auth fields)
3. docs/razorpay_event_flow.png (Razorpay Event Flow: Webhook -> Verification -> Redis -> Orchestrator -> Razorpay Execution)
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
os.makedirs(DOCS_DIR, exist_ok=True)


def generate_architecture_diagram():
    """Generates 5-Agent + Supabase + Redis Architecture Diagram."""
    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a") # Slate 900

    # Title
    ax.text(7, 8.5, "GrowthPilot — Autonomous AI Commerce Multi-Agent Architecture",
            fontsize=16, fontweight="bold", color="#ffffff", ha="center")
    ax.text(7, 8.1, "Phase 3: Supabase Postgres (RLS) + Redis Queue/Cache + Razorpay Test Execution",
            fontsize=10, color="#94a3b8", ha="center")

    # Layer 1: Client & Auth (Top Left)
    rect1 = patches.FancyBboxPatch((0.5, 5.5), 3.2, 2.0, boxstyle="round,pad=0.2",
                                  facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2)
    ax.add_patch(rect1)
    ax.text(2.1, 7.1, "CLIENT & AUTH LAYER", fontsize=11, fontweight="bold", color="#38bdf8", ha="center")
    ax.text(2.1, 6.6, "• Next.js / HTML5 Dashboard", fontsize=9, color="#e2e8f0", ha="center")
    ax.text(2.1, 6.2, "• Supabase JWT (RS256/HS256)", fontsize=9, color="#e2e8f0", ha="center")
    ax.text(2.1, 5.8, "• Derived tenant_id Header", fontsize=9, color="#e2e8f0", ha="center")

    # Layer 2: API Gateway & Rate Limiting (Middle Left)
    rect2 = patches.FancyBboxPatch((4.2, 5.5), 3.5, 2.0, boxstyle="round,pad=0.2",
                                  facecolor="#1e293b", edgecolor="#818cf8", linewidth=2)
    ax.add_patch(rect2)
    ax.text(5.95, 7.1, "FASTAPI API GATEWAY", fontsize=11, fontweight="bold", color="#818cf8", ha="center")
    ax.text(5.95, 6.6, "• get_current_tenant Dependency", fontsize=9, color="#e2e8f0", ha="center")
    ax.text(5.95, 6.2, "• Per-Tenant Redis Rate Limiting", fontsize=9, color="#e2e8f0", ha="center")
    ax.text(5.95, 5.8, "• 30-60s Redis Cache (Overview)", fontsize=9, color="#e2e8f0", ha="center")

    # Layer 3: 5-Agent Core Engine (Right)
    rect3 = patches.FancyBboxPatch((8.2, 3.2), 5.3, 4.3, boxstyle="round,pad=0.2",
                                  facecolor="#1e293b", edgecolor="#34d399", linewidth=2)
    ax.add_patch(rect3)
    ax.text(10.85, 7.1, "5-AGENT AI REASONING CORE", fontsize=11, fontweight="bold", color="#34d399", ha="center")
    
    agent_boxes = [
        ("1. Insight Agent", "Funnel anomaly & RFM segmentation", 6.4),
        ("2. Growth Decision Agent", "Priority = Impact * Conf * Urgency", 5.6),
        ("3. Campaign & Pricing Agent", "Dynamic discount band (margin + inventory)", 4.8),
        ("4. Guardrail & Orchestrator", "Human-in-the-loop approval & RZP dispatch", 4.0),
        ("5. Experiment Agent", "Pre-registered hypothesis vs actuals", 3.2)
    ]
    for name, desc, y_pos in agent_boxes:
        r = patches.FancyBboxPatch((8.5, y_pos - 0.25), 4.7, 0.6, boxstyle="round,pad=0.1",
                                   facecolor="#0f172a", edgecolor="#475569", linewidth=1)
        ax.add_patch(r)
        ax.text(8.7, y_pos + 0.05, name, fontsize=8.5, fontweight="bold", color="#38bdf8")
        ax.text(8.7, y_pos - 0.15, desc, fontsize=7.5, color="#94a3b8")

    # Layer 4: Storage & Infrastructure (Bottom Left)
    rect4 = patches.FancyBboxPatch((0.5, 0.8), 7.2, 3.8, boxstyle="round,pad=0.2",
                                  facecolor="#1e293b", edgecolor="#fbbf24", linewidth=2)
    ax.add_patch(rect4)
    ax.text(4.1, 4.2, "STORAGE & EVENT INFRASTRUCTURE", fontsize=11, fontweight="bold", color="#fbbf24", ha="center")

    # Supabase Box
    r_supa = patches.FancyBboxPatch((0.8, 1.2), 3.2, 2.6, boxstyle="round,pad=0.1",
                                    facecolor="#0f172a", edgecolor="#10b981", linewidth=1.5)
    ax.add_patch(r_supa)
    ax.text(2.4, 3.4, "Supabase Postgres", fontsize=9.5, fontweight="bold", color="#34d399", ha="center")
    ax.text(2.4, 2.9, "• Row Level Security (RLS)\n• tenant_id indexed on all 12 tables\n• Alembic versioned migrations\n• SQLite offline fallback",
            fontsize=7.5, color="#cbd5e1", ha="center")

    # Redis Box
    r_redis = patches.FancyBboxPatch((4.3, 1.2), 3.1, 2.6, boxstyle="round,pad=0.1",
                                     facecolor="#0f172a", edgecolor="#f87171", linewidth=1.5)
    ax.add_patch(r_redis)
    ax.text(5.85, 3.4, "Redis Queue & Cache", fontsize=9.5, fontweight="bold", color="#f87171", ha="center")
    ax.text(5.85, 2.9, "• growthpilot:events:queue\n• Async Background Worker\n• Per-Tenant Rate Limiting\n• 45s Query Cache + Invalidation",
            fontsize=7.5, color="#cbd5e1", ha="center")

    # Razorpay Integration Box (Bottom Right)
    rect5 = patches.FancyBboxPatch((8.2, 0.8), 5.3, 2.0, boxstyle="round,pad=0.2",
                                  facecolor="#1e293b", edgecolor="#60a5fa", linewidth=2)
    ax.add_patch(rect5)
    ax.text(10.85, 2.4, "RAZORPAY TEST-MODE EXECUTION", fontsize=11, fontweight="bold", color="#60a5fa", ha="center")
    ax.text(10.85, 1.9, "• Test-Mode Orders & Dynamic Payment Links API", fontsize=8.5, color="#e2e8f0", ha="center")
    ax.text(10.85, 1.5, "• HMAC-SHA256 Webhook Verification & SHA-256 Payload Hashing", fontsize=8, color="#cbd5e1", ha="center")
    ax.text(10.85, 1.1, "• payment.failed Penalty (-0.08 confidence)", fontsize=8, color="#cbd5e1", ha="center")

    # Connecting Arrows
    arrow_style = dict(arrowstyle="->", color="#94a3b8", lw=1.5)
    ax.annotate("", xy=(4.2, 6.5), xytext=(3.7, 6.5), arrowprops=arrow_style)
    ax.annotate("", xy=(8.2, 6.5), xytext=(7.7, 6.5), arrowprops=arrow_style)
    ax.annotate("", xy=(4.1, 4.6), xytext=(4.1, 5.5), arrowprops=arrow_style)
    ax.annotate("", xy=(10.85, 3.2), xytext=(10.85, 2.8), arrowprops=arrow_style)

    plt.tight_layout()
    out_path = os.path.join(DOCS_DIR, "architecture_diagram.png")
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated {out_path}")


def generate_er_diagram():
    """Generates Database ER Diagram with multi-tenant tenant_id & auth fields."""
    fig, ax = plt.subplots(figsize=(14, 9), dpi=200)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a")

    # Title
    ax.text(7, 9.5, "GrowthPilot — Multi-Tenant Relational Database ER Diagram",
            fontsize=15, fontweight="bold", color="#ffffff", ha="center")
    ax.text(7, 9.1, "Supabase Postgres / SQLite Schema with tenant_id RLS and Razorpay Execution Fields",
            fontsize=9.5, color="#94a3b8", ha="center")

    def draw_table(x, y, w, h, title, columns, header_color="#0284c7"):
        r_head = patches.FancyBboxPatch((x, y + h - 0.5), w, 0.5, boxstyle="round,pad=0.05",
                                        facecolor=header_color, edgecolor="none")
        r_body = patches.FancyBboxPatch((x, y), w, h - 0.5, boxstyle="round,pad=0.05",
                                        facecolor="#1e293b", edgecolor="#334155", linewidth=1.5)
        ax.add_patch(r_body)
        ax.add_patch(r_head)
        ax.text(x + w / 2, y + h - 0.28, title, fontsize=9, fontweight="bold", color="#ffffff", ha="center")
        
        y_text = y + h - 0.75
        for col, is_pk, is_tenant in columns:
            prefix = "🔑 " if is_pk else ("🏢 " if is_tenant else "  ")
            color = "#38bdf8" if is_pk else ("#fbbf24" if is_tenant else "#e2e8f0")
            ax.text(x + 0.15, y_text, f"{prefix}{col}", fontsize=7.5, color=color, fontfamily="monospace")
            y_text -= 0.28

    # Tables
    # Row 1
    draw_table(0.5, 6.0, 2.8, 2.7, "CUSTOMERS", [
        ("customer_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("age : INT", False, False),
        ("segment : TEXT", False, False),
        ("channel : TEXT", False, False),
        ("signup_date : TEXT", False, False),
    ], "#0284c7")

    draw_table(3.6, 5.8, 3.2, 2.9, "PRODUCTS", [
        ("product_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("name : TEXT", False, False),
        ("category : TEXT", False, False),
        ("base_price : REAL", False, False),
        ("margin_pct : REAL", False, False),
        ("inventory_count : INT", False, False),
        ("inventory_urgency : REAL", False, False),
    ], "#0284c7")

    draw_table(7.1, 5.8, 3.2, 2.9, "ORDER_ITEMS", [
        ("order_item_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("customer_id (FK)", False, False),
        ("product_id (FK)", False, False),
        ("purchase_date : TEXT", False, False),
        ("quantity : INT", False, False),
        ("discount_pct : REAL", False, False),
        ("revenue : REAL", False, False),
    ], "#0284c7")

    draw_table(10.6, 6.0, 2.9, 2.7, "SESSIONS", [
        ("session_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("customer_id (FK)", False, False),
        ("start_time : TEXT", False, False),
        ("channel : TEXT", False, False),
    ], "#0284c7")

    # Row 2
    draw_table(0.5, 2.7, 2.8, 2.8, "CART_EVENTS", [
        ("cart_event_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("session_id (FK)", False, False),
        ("customer_id : TEXT", False, False),
        ("product_id (FK)", False, False),
        ("event_type : TEXT", False, False),
        ("event_time : TEXT", False, False),
    ], "#0d9488")

    draw_table(3.6, 2.5, 3.2, 3.0, "OPPORTUNITIES", [
        ("opportunity_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("insight_id (FK)", False, False),
        ("problem : TEXT", False, False),
        ("expected_impact : REAL", False, False),
        ("confidence : REAL", False, False),
        ("urgency_factor : REAL", False, False),
        ("priority_score : REAL", False, False),
        ("status : TEXT", False, False),
    ], "#0d9488")

    draw_table(7.1, 2.5, 3.2, 3.0, "CAMPAIGN_PROPOSALS", [
        ("campaign_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("opportunity_id (FK)", False, False),
        ("target_segment : TEXT", False, False),
        ("product_id : TEXT", False, False),
        ("offer_pct : REAL", False, False),
        ("discount_band : JSON", False, False),
        ("risk_tier : TEXT", False, False),
        ("status : TEXT", False, False),
    ], "#0d9488")

    draw_table(10.6, 2.5, 2.9, 3.0, "EXECUTIONS", [
        ("execution_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("campaign_id (FK)", False, False),
        ("approved_by : TEXT", False, False),
        ("razorpay_order_id", False, False),
        ("razorpay_link_id", False, False),
        ("execution_token : TEXT", False, False),
        ("status : TEXT", False, False),
    ], "#0d9488")

    # Row 3 (Audit & Results)
    draw_table(0.5, 0.4, 4.5, 1.8, "EXPERIMENT_RESULTS", [
        ("result_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("execution_id (FK)", False, False),
        ("verdict : TEXT", False, False),
        ("ai_reasoning : TEXT", False, False),
    ], "#7c3aed")

    draw_table(5.3, 0.4, 4.5, 1.8, "AUDIT_LOGS", [
        ("log_id (PK)", True, False),
        ("tenant_id (FK/RLS)", False, True),
        ("timestamp : TEXT", False, False),
        ("agent_or_user : TEXT", False, False),
        ("payload_hash : SHA256", False, False),
        ("details : JSON (Sanitized)", False, False),
    ], "#7c3aed")

    # Legend
    ax.text(10.2, 1.2, "Legend:", fontsize=8.5, fontweight="bold", color="#ffffff")
    ax.text(10.2, 0.8, "🔑 Primary Key\n🏢 tenant_id (RLS Isolation Policy)", fontsize=7.5, color="#fbbf24")

    plt.tight_layout()
    out_path = os.path.join(DOCS_DIR, "er_diagram.png")
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated {out_path}")


def generate_razorpay_event_flow():
    """Generates Razorpay Event Flow Diagram."""
    fig, ax = plt.subplots(figsize=(14, 5.5), dpi=200)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a")

    # Title
    ax.text(7, 5.4, "GrowthPilot — Razorpay Event-Driven Pipeline Execution Flow",
            fontsize=15, fontweight="bold", color="#ffffff", ha="center")
    ax.text(7, 5.0, "Webhook → Signature Verification → Redis Queue → Worker → Orchestrator → Razorpay Execution",
            fontsize=9.5, color="#94a3b8", ha="center")

    steps = [
        ("1. Razorpay Event", "payment.captured\npayment.failed\norder.paid", "#38bdf8", 0.6),
        ("2. Signature Check", "HMAC-SHA256\nVerify secret\nSHA-256 Hash", "#818cf8", 3.0),
        ("3. Redis Queue", "growthpilot:events\nEnqueue event\nNon-blocking 200", "#f87171", 5.4),
        ("4. Background Worker", "Worker thread\nPop event\nTrigger pipeline", "#fbbf24", 7.8),
        ("5. Agent Orchestrator", "Re-score confidence\nDraft/Update play\nDynamic discount", "#34d399", 10.2),
        ("6. Razorpay API", "Create Order\nGenerate PayLink\nAudit Log Record", "#a78bfa", 12.6)
    ]

    for title, desc, color, x in steps:
        r = patches.FancyBboxPatch((x - 0.9, 1.6), 2.0, 2.6, boxstyle="round,pad=0.15",
                                   facecolor="#1e293b", edgecolor=color, linewidth=2)
        ax.add_patch(r)
        ax.text(x + 0.1, 3.8, title, fontsize=9.5, fontweight="bold", color=color, ha="center")
        ax.text(x + 0.1, 2.5, desc, fontsize=8, color="#e2e8f0", ha="center", va="center")

    # Connecting Arrows
    for i in range(len(steps) - 1):
        x_start = steps[i][3] + 1.2
        x_end = steps[i+1][3] - 1.0
        ax.annotate("", xy=(x_end, 2.9), xytext=(x_start, 2.9),
                    arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=2))

    # Bottom Callout
    r_bot = patches.FancyBboxPatch((1.5, 0.4), 11.0, 0.8, boxstyle="round,pad=0.1",
                                   facecolor="#0f172a", edgecolor="#475569", linewidth=1)
    ax.add_patch(r_bot)
    ax.text(7, 0.8, "Failure Handling: If payment.failed is received, Orchestrator applies confidence degradation penalty (-0.08) and updates execution records.",
            fontsize=8, color="#fca5a5", ha="center")

    plt.tight_layout()
    out_path = os.path.join(DOCS_DIR, "razorpay_event_flow.png")
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated {out_path}")


if __name__ == "__main__":
    generate_architecture_diagram()
    generate_er_diagram()
    generate_razorpay_event_flow()
