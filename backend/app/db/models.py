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

    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id TEXT PRIMARY KEY,
        tenant_id TEXT DEFAULT 'tenant_store_alpha',
        customer_id TEXT,
        product_id TEXT,
        purchase_date TEXT,
        quantity INTEGER,
        discount_pct REAL,
        revenue REAL,
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
        details TEXT
    );
    """)

    def add_column_if_not_exists(table, column, col_type):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass

    tables = [
        "customers", "products", "order_items", "sessions", "cart_events",
        "insights", "opportunities", "campaign_proposals", "campaign_interactions",
        "executions", "experiment_results", "audit_logs"
    ]
    for tbl in tables:
        add_column_if_not_exists(tbl, "tenant_id", "TEXT DEFAULT 'tenant_store_alpha'")

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
    tenant_id: str = DEFAULT_TENANT_ID
):
    """Logs an agent decision, webhook, or human action into the audit trail with sanitized details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    sanitized = sanitize_details(details)
    cursor.execute("""
        INSERT INTO audit_logs (log_id, tenant_id, timestamp, agent_or_user, action_type, payload_hash, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (log_id, tenant_id, datetime.now().isoformat(), agent_or_user, action_type, payload_hash, json.dumps(sanitized)))
    conn.commit()
    conn.close()
