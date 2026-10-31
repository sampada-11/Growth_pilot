"""
Database Engine & Connection Manager (Supabase Postgres + SQLite Fallback)
Supports SQLAlchemy, RLS (Row Level Security), and tenant context.
"""
import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Environment configuration
DEFAULT_TENANT_ID = os.environ.get("DEMO_TENANT_ID", "tenant_demo_001")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'growthpilot.db'))}"
)

# Handle Postgres dialect url formatting (e.g. postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db_engine():
    return engine


def get_db() -> Generator:
    """FastAPI dependency for obtaining a database session with tenant context."""
    db = SessionLocal()
    try:
        # If Postgres, set tenant context for RLS
        if "postgresql" in str(engine.url):
            db.execute(text(f"SET LOCAL app.current_tenant = '{DEFAULT_TENANT_ID}';"))
        yield db
    finally:
        db.close()


@contextmanager
def db_session_scope(tenant_id: str = DEFAULT_TENANT_ID):
    """Context manager for background tasks/agents with tenant context."""
    db = SessionLocal()
    try:
        if "postgresql" in str(engine.url):
            db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def setup_supabase_rls(db_engine=engine):
    """
    Sets up Row Level Security (RLS) policies on Supabase Postgres for all business tables.
    """
    if "postgresql" not in str(db_engine.url):
        return

    tables = [
        "customers", "products", "order_items", "sessions", "cart_events",
        "insights", "opportunities", "campaign_proposals", "campaign_interactions",
        "executions", "experiment_results", "audit_logs",
        "payments", "segments", "agent_runs", "agent_steps", "campaigns",
        "campaign_content", "campaign_deliveries", "experiments",
        "experiment_assignments", "learning_signals", "copilot_messages",
        "opportunity_events"
    ]

    with db_engine.connect() as conn:
        for tbl in tables:
            conn.execute(text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;"))
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};"))
            conn.execute(text(f"""
                CREATE POLICY tenant_isolation_policy ON {tbl}
                AS PERMISSIVE FOR ALL
                USING (tenant_id = current_setting('app.current_tenant', true))
                WITH CHECK (tenant_id = current_setting('app.current_tenant', true));
            """))
        conn.commit()
    print("[Database] Supabase Postgres RLS policies enabled and applied.")
