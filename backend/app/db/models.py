"""
Database Models & SQLite Schema for GrowthPilot
Extended with Phase 1: Razorpay Integration & Phase 2: Supabase Postgres/Multi-Tenant Schema
"""
import sqlite3
import json
import os
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "growthpilot.db")
DEFAULT_TENANT_ID = os.environ.get("DEMO_TENANT_ID", "tenant_store_alpha")


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=60000;")
    return conn


def init_db():
    """Creates SQLite database tables according to ER Diagram + Razorpay & Multi-Tenant extensions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        age INTEGER,
        segment TEXT,
        channel TEXT,
        signup_date TEXT
    );

    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        name TEXT,
        category TEXT,
        base_price REAL,
        margin_pct REAL DEFAULT 40.0,
        inventory_count INTEGER DEFAULT 100,
        inventory_urgency_factor REAL DEFAULT 1.0,
        launch_date TEXT
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        customer_id TEXT,
        order_date TEXT,
        total_amount REAL,
        status TEXT DEFAULT 'completed',
        created_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        order_id TEXT,
        customer_id TEXT,
        product_id TEXT,
        purchase_date TEXT,
        quantity INTEGER,
        unit_price REAL,
        discount_pct REAL,
        revenue REAL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        customer_id TEXT,
        start_time TEXT,
        channel TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE IF NOT EXISTS cart_events (
        cart_event_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        session_id TEXT,
        customer_id TEXT,
        product_id TEXT,
        event_type TEXT,
        event_time TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    CREATE TABLE IF NOT EXISTS insights (
        insight_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        type TEXT,
        description TEXT,
        evidence TEXT,
        generated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS opportunities (
        opportunity_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        insight_id TEXT,
        problem TEXT,
        expected_impact REAL,
        confidence REAL,
        urgency_factor REAL DEFAULT 1.0,
        recommended_action TEXT,
        priority_score REAL,
        priority_rank INTEGER,
        status TEXT DEFAULT 'open',
        FOREIGN KEY (insight_id) REFERENCES insights(insight_id)
    );

    CREATE TABLE IF NOT EXISTS campaign_proposals (
        campaign_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        opportunity_id TEXT,
        target_segment TEXT,
        product_id TEXT,
        offer_pct REAL,
        discount_band TEXT,
        channel TEXT,
        generated_copy TEXT,
        expected_roi REAL,
        risk_tier TEXT,
        risk_reasons TEXT,
        status TEXT DEFAULT 'drafted',
        created_at TEXT,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id)
    );

    CREATE TABLE IF NOT EXISTS campaign_interactions (
        interaction_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        campaign_id TEXT,
        customer_id TEXT,
        interaction_type TEXT,
        interaction_time TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaign_proposals(campaign_id),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE IF NOT EXISTS executions (
        execution_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        campaign_id TEXT,
        approved_by TEXT,
        justification TEXT,
        executed_at TEXT,
        mock_api_status TEXT,
        execution_token TEXT,
        razorpay_order_id TEXT,
        razorpay_payment_link_id TEXT,
        razorpay_payment_id TEXT,
        status TEXT DEFAULT 'executed',
        error_message TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaign_proposals(campaign_id)
    );

    CREATE TABLE IF NOT EXISTS experiment_results (
        result_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        execution_id TEXT,
        expected_conversion REAL,
        actual_conversion REAL,
        expected_revenue REAL,
        actual_revenue REAL,
        verdict TEXT,
        ai_reasoning TEXT,
        evaluated_at TEXT,
        FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        timestamp TEXT,
        agent_or_user TEXT,
        action_type TEXT,
        payload_hash TEXT,
        details TEXT,
        event_type TEXT,
        actor_type TEXT DEFAULT 'user',
        actor_id TEXT,
        entity_type TEXT,
        entity_id TEXT,
        status TEXT DEFAULT 'success'
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        order_id TEXT,
        provider_event_id TEXT,
        amount REAL,
        currency TEXT DEFAULT 'INR',
        status TEXT DEFAULT 'succeeded',
        is_simulated INTEGER DEFAULT 1,
        created_at TEXT,
        UNIQUE(tenant_id, provider_event_id)
    );

    CREATE TABLE IF NOT EXISTS segments (
        segment_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        name TEXT NOT NULL,
        definition TEXT,
        is_system INTEGER DEFAULT 1,
        created_at TEXT,
        UNIQUE(tenant_id, name)
    );

    CREATE TABLE IF NOT EXISTS agent_runs (
        run_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        status TEXT DEFAULT 'pending',
        started_at TEXT,
        completed_at TEXT,
        summary TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS agent_steps (
        step_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        agent TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        input_hash TEXT,
        input_data TEXT,
        output_data TEXT,
        latency_ms INTEGER DEFAULT 0,
        tokens_used INTEGER DEFAULT 0,
        error TEXT,
        created_at TEXT,
        FOREIGN KEY (run_id) REFERENCES agent_runs(run_id)
    );

    CREATE TABLE IF NOT EXISTS campaigns (
        campaign_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        opportunity_id TEXT,
        name TEXT,
        objective TEXT DEFAULT 'recover_abandoned_carts',
        segment_id TEXT,
        mode TEXT DEFAULT 'demo',
        status TEXT DEFAULT 'draft',
        discount TEXT,
        budget_total REAL DEFAULT 0.0,
        per_customer_cap REAL DEFAULT 0.0,
        scheduled_at TEXT,
        version INTEGER DEFAULT 1,
        is_simulated INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS campaign_content (
        content_id TEXT PRIMARY KEY,
        campaign_id TEXT NOT NULL,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        channel TEXT NOT NULL,
        variant TEXT NOT NULL,
        subject TEXT,
        preheader TEXT,
        body TEXT NOT NULL,
        cta TEXT NOT NULL,
        source TEXT DEFAULT 'ai',
        lint_result TEXT,
        created_at TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
    );

    CREATE TABLE IF NOT EXISTS campaign_deliveries (
        delivery_id TEXT PRIMARY KEY,
        campaign_id TEXT NOT NULL,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        customer_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        status TEXT DEFAULT 'queued',
        provider_message_id TEXT,
        idempotency_key TEXT UNIQUE,
        is_simulated INTEGER DEFAULT 1,
        status_at TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS experiments (
        experiment_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        campaign_id TEXT NOT NULL,
        holdout_pct REAL DEFAULT 20.0,
        start_at TEXT,
        end_at TEXT,
        status TEXT DEFAULT 'running',
        verdict TEXT,
        result TEXT,
        is_simulated INTEGER DEFAULT 1,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS experiment_assignments (
        assignment_id TEXT PRIMARY KEY,
        experiment_id TEXT NOT NULL,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        customer_id TEXT NOT NULL,
        arm TEXT NOT NULL,
        assigned_at TEXT,
        UNIQUE(experiment_id, customer_id)
    );

    CREATE TABLE IF NOT EXISTS learning_signals (
        signal_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        opportunity_type TEXT NOT NULL,
        product_id TEXT,
        segment_key TEXT,
        observed_uplift REAL,
        sample_size INTEGER,
        source_experiment_id TEXT,
        is_simulated INTEGER DEFAULT 1,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS copilot_messages (
        message_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        tool_calls TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS opportunity_events (
        event_id TEXT PRIMARY KEY,
        opportunity_id TEXT NOT NULL,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        from_state TEXT,
        to_state TEXT,
        actor_id TEXT,
        reason TEXT,
        occurred_at TEXT
    );
    """)

    def add_column_if_not_exists(table, column, col_type):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass

    tables = [
        "customers", "products", "orders", "order_items", "sessions", "cart_events",
        "insights", "opportunities", "campaign_proposals", "campaign_interactions",
        "executions", "experiment_results", "audit_logs",
        "payments", "segments", "agent_runs", "agent_steps", "campaigns",
        "campaign_content", "campaign_deliveries", "experiments",
        "experiment_assignments", "learning_signals", "copilot_messages",
        "opportunity_events"
    ]
    for tbl in tables:
        add_column_if_not_exists(tbl, "tenant_id", "TEXT DEFAULT 'tenant_store_alpha'")

    # Core dataset extensions (§A)
    add_column_if_not_exists("customers", "location", "TEXT")
    add_column_if_not_exists("customers", "registration_date", "TEXT")
    add_column_if_not_exists("products", "price", "REAL")
    add_column_if_not_exists("products", "stock", "INTEGER DEFAULT 100")
    add_column_if_not_exists("orders", "status", "TEXT DEFAULT 'completed'")
    add_column_if_not_exists("orders", "total_amount", "REAL DEFAULT 0.0")
    add_column_if_not_exists("order_items", "order_id", "TEXT")
    add_column_if_not_exists("order_items", "unit_price", "REAL DEFAULT 0.0")
    add_column_if_not_exists("sessions", "session_status", "TEXT DEFAULT 'completed'")
    add_column_if_not_exists("cart_events", "timestamp", "TEXT")
    add_column_if_not_exists("campaigns", "segment", "TEXT")

    add_column_if_not_exists("products", "margin_pct", "REAL DEFAULT 40.0")
    add_column_if_not_exists("products", "inventory_count", "INTEGER DEFAULT 100")
    add_column_if_not_exists("products", "inventory_urgency_factor", "REAL DEFAULT 1.0")
    add_column_if_not_exists("campaign_proposals", "discount_band", "TEXT")
    add_column_if_not_exists("executions", "razorpay_order_id", "TEXT")
    add_column_if_not_exists("executions", "razorpay_payment_link_id", "TEXT")
    add_column_if_not_exists("executions", "razorpay_payment_id", "TEXT")
    add_column_if_not_exists("executions", "status", "TEXT DEFAULT 'executed'")
    add_column_if_not_exists("executions", "error_message", "TEXT")
    add_column_if_not_exists("audit_logs", "payload_hash", "TEXT")
    add_column_if_not_exists("audit_logs", "event_type", "TEXT")
    add_column_if_not_exists("audit_logs", "actor_type", "TEXT DEFAULT 'user'")
    add_column_if_not_exists("audit_logs", "actor_id", "TEXT")
    add_column_if_not_exists("audit_logs", "entity_type", "TEXT")
    add_column_if_not_exists("audit_logs", "entity_id", "TEXT")
    add_column_if_not_exists("audit_logs", "status", "TEXT DEFAULT 'success'")

    # Extended columns for opportunities
    add_column_if_not_exists("opportunities", "title", "TEXT")
    add_column_if_not_exists("opportunities", "description", "TEXT")
    add_column_if_not_exists("opportunities", "root_cause", "TEXT")
    add_column_if_not_exists("opportunities", "affected_customers", "TEXT")
    add_column_if_not_exists("opportunities", "product_id", "TEXT")
    add_column_if_not_exists("opportunities", "supporting_analytics", "TEXT")
    add_column_if_not_exists("opportunities", "strategy", "TEXT")
    add_column_if_not_exists("opportunities", "est_revenue_impact", "REAL DEFAULT 0.0")
    add_column_if_not_exists("opportunities", "est_profit_impact", "REAL DEFAULT 0.0")
    add_column_if_not_exists("opportunities", "risk_level", "TEXT DEFAULT 'medium'")
    add_column_if_not_exists("opportunities", "approval_status", "TEXT DEFAULT 'pending'")
    add_column_if_not_exists("opportunities", "execution_status", "TEXT DEFAULT 'not_started'")
    add_column_if_not_exists("opportunities", "lifecycle_state", "TEXT DEFAULT 'detected'")
    add_column_if_not_exists("opportunities", "agent_run_id", "TEXT")
    add_column_if_not_exists("opportunities", "guardrail_result", "TEXT")
    add_column_if_not_exists("opportunities", "impact_inputs", "TEXT")
    add_column_if_not_exists("opportunities", "approved_by", "TEXT")
    add_column_if_not_exists("opportunities", "rejected_by", "TEXT")
    add_column_if_not_exists("opportunities", "rejection_reason", "TEXT")
    add_column_if_not_exists("opportunities", "created_at", "TEXT")
    add_column_if_not_exists("opportunities", "updated_at", "TEXT")

    # Extended columns for campaigns
    add_column_if_not_exists("campaigns", "audience_size", "INTEGER DEFAULT 0")
    add_column_if_not_exists("campaigns", "guardrail_result", "TEXT")
    add_column_if_not_exists("campaigns", "approved_by", "TEXT")

    conn.commit()
    conn.close()


def sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Removes sensitive payment data before logging."""
    sensitive_keys = {"card", "cvv", "card_number", "secret", "password", "key_secret"}
    sanitized = {}
    for k, v in details.items():
        if any(s in k.lower() for s in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_details(v)
        else:
            sanitized[k] = v
    return sanitized


def log_audit(
    agent_or_user: str,
    action_type: str,
    details: Dict[str, Any],
    payload_hash: Optional[str] = None,
    tenant_id: str = DEFAULT_TENANT_ID,
    event_type: Optional[str] = None,
    actor_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: str = "success"
):
    """Logs an agent decision, webhook, or human action into the audit trail with sanitized details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    sanitized = sanitize_details(details)

    eff_event_type = event_type or action_type.lower().replace(" ", "_")
    eff_actor_id = actor_id or agent_or_user
    if not actor_type:
        eff_actor_type = "agent" if "agent" in agent_or_user.lower() or "orchestrator" in agent_or_user.lower() else "user"
    else:
        eff_actor_type = actor_type

    cursor.execute("""
        INSERT INTO audit_logs (
            log_id, tenant_id, timestamp, agent_or_user, action_type, payload_hash, details,
            event_type, actor_type, actor_id, entity_type, entity_id, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id, tenant_id, datetime.now().isoformat(), agent_or_user, action_type, payload_hash,
        json.dumps(sanitized), eff_event_type, eff_actor_type, eff_actor_id, entity_type, entity_id, status
    ))
    conn.commit()
    conn.close()
