"""
Phase 1 Test Suite: Database Schema Extensions, Multi-Entity Tables, and Centralized Audit Logging
Validates PRD Section 12 & Module G (FR-062 to FR-065).
"""
import pytest
import sqlite3
from backend.app.db.models import init_db, get_db_connection
from backend.app.audit.service import record_audit_event, query_audit_events


class TestPhase1SchemaAndAudit:

    @pytest.fixture(autouse=True)
    def setup_database(self):
        init_db()

    def test_01_all_prd_tables_exist(self):
        """Verifies that all 12+ required PRD tables exist in the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {
            "customers", "products", "order_items", "sessions", "cart_events",
            "insights", "opportunities", "campaign_proposals", "campaign_interactions",
            "executions", "experiment_results", "audit_logs",
            "payments", "segments", "agent_runs", "agent_steps", "campaigns",
            "campaign_content", "campaign_deliveries", "experiments",
            "experiment_assignments", "learning_signals", "copilot_messages",
            "opportunity_events"
        }
        for tbl in expected_tables:
            assert tbl in tables, f"Mandatory table '{tbl}' missing from database schema"

    def test_02_opportunity_extended_columns(self):
        """Verifies that opportunities table contains all lifecycle, impact, and strategy columns."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(opportunities)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        required_cols = [
            "opportunity_id", "tenant_id", "problem", "root_cause",
            "affected_customers", "product_id", "supporting_analytics",
            "strategy", "est_revenue_impact", "est_profit_impact",
            "confidence", "priority_score", "risk_level", "approval_status",
            "execution_status", "lifecycle_state", "guardrail_result",
            "impact_inputs"
        ]
        for col in required_cols:
            assert col in columns, f"Column '{col}' missing from opportunities table"

    def test_03_audit_log_extended_columns(self):
        """Verifies that audit_logs contains structured metadata fields."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(audit_logs)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        required_cols = [
            "log_id", "tenant_id", "timestamp", "agent_or_user",
            "action_type", "payload_hash", "details", "event_type",
            "actor_type", "actor_id", "status"
        ]
        for col in required_cols:
            assert col in columns, f"Column '{col}' missing from audit_logs table"

    def test_04_audit_service_record_and_query_filtering(self):
        """Validates that record_audit_event records typed events and query_audit_events filters by tenant."""
        tenant_a = "test_tenant_alpha"
        tenant_b = "test_tenant_beta"

        # Record events for Tenant A
        log_a1 = record_audit_event(
            tenant_id=tenant_a,
            event_type="agent.run_started",
            actor_id="Orchestrator Agent",
            actor_type="agent",
            entity_type="run",
            entity_id="RUN-001",
            metadata={"step": "CIA_PIA_parallel"}
        )

        log_a2 = record_audit_event(
            tenant_id=tenant_a,
            event_type="guardrail.decision",
            actor_id="Guardrail Agent",
            actor_type="agent",
            entity_type="opportunity",
            entity_id="OPP-001",
            status="ALLOW",
            metadata={"decision": "ALLOW", "rule": "GR-01"}
        )

        # Record event for Tenant B
        log_b1 = record_audit_event(
            tenant_id=tenant_b,
            event_type="agent.run_started",
            actor_id="Orchestrator Agent",
            actor_type="agent",
            entity_type="run",
            entity_id="RUN-B01",
            metadata={"step": "start"}
        )

        # Query Tenant A
        events_a, total_a = query_audit_events(tenant_id=tenant_a)
        log_ids_a = [e["log_id"] for e in events_a]
        assert log_a1 in log_ids_a
        assert log_a2 in log_ids_a
        assert log_b1 not in log_ids_a, "Tenant B event leaked into Tenant A query!"

        # Filter by event_type for Tenant A
        filtered_events, filtered_total = query_audit_events(
            tenant_id=tenant_a,
            event_type="guardrail.decision"
        )
        assert len(filtered_events) >= 1
        assert all(e["event_type"] == "guardrail.decision" for e in filtered_events)

    def test_05_payments_idempotency_constraint(self):
        """Verifies that payments table enforces unique(tenant_id, provider_event_id)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO payments (payment_id, tenant_id, order_id, provider_event_id, amount, status, is_simulated, created_at)
            VALUES ('pay_1', 'tenant_test_1', 'ord_1', 'evt_123', 1000.0, 'succeeded', 1, '2026-10-30T10:00:00Z')
        """)
        conn.commit()

        # Duplicate insert on same tenant and provider_event_id with INSERT must raise IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO payments (payment_id, tenant_id, order_id, provider_event_id, amount, status, is_simulated, created_at)
                VALUES ('pay_2', 'tenant_test_1', 'ord_1', 'evt_123', 1000.0, 'succeeded', 1, '2026-10-30T10:00:00Z')
            """)
            conn.commit()
        conn.close()

