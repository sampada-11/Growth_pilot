"""
Audit & Activity Service (Module G — FR-062 to FR-065)
Provides tamper-evident, append-only audit event logging and structured filtering.
"""
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from backend.app.db.models import get_db_connection, log_audit, sanitize_details


def record_audit_event(
    tenant_id: str,
    event_type: str,
    actor_id: str,
    actor_type: str = "user",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
    payload_hash: Optional[str] = None
) -> str:
    """
    Appends an immutable audit event to audit_logs scoped to tenant_id.
    Returns the generated log_id.
    """
    log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    details = metadata or {}
    sanitized = sanitize_details(details)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (
            log_id, tenant_id, timestamp, agent_or_user, action_type, payload_hash, details,
            event_type, actor_type, actor_id, entity_type, entity_id, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id, tenant_id, datetime.now().isoformat(), actor_id, event_type, payload_hash,
        json.dumps(sanitized), event_type, actor_type, actor_id, entity_type, entity_id, status
    ))
    conn.commit()
    conn.close()
    return log_id


def query_audit_events(
    tenant_id: str,
    event_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_type: Optional[str] = None,
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Queries audit logs for tenant_id with multi-field filtering, search, and pagination.
    Returns: (events_list, total_count)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = ["tenant_id = ?"]
    params: List[Any] = [tenant_id]

    if event_type:
        conditions.append("(event_type = ? OR action_type = ?)")
        params.extend([event_type, event_type])

    if actor_id:
        conditions.append("(actor_id = ? OR agent_or_user = ?)")
        params.extend([actor_id, actor_id])

    if actor_type:
        conditions.append("actor_type = ?")
        params.append(actor_type)

    if status:
        conditions.append("status = ?")
        params.append(status)

    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)

    if entity_id:
        conditions.append("entity_id = ?")
        params.append(entity_id)

    if date_from:
        conditions.append("timestamp >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("timestamp <= ?")
        params.append(date_to)

    if search:
        search_like = f"%{search}%"
        conditions.append("(action_type LIKE ? OR event_type LIKE ? OR details LIKE ? OR agent_or_user LIKE ?)")
        params.extend([search_like, search_like, search_like, search_like])

    where_clause = " AND ".join(conditions)

    # Count total matching
    count_sql = f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}"
    cursor.execute(count_sql, tuple(params))
    total_count = cursor.fetchone()[0]

    # Fetch rows
    fetch_sql = f"""
        SELECT * FROM audit_logs 
        WHERE {where_clause} 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
    """
    params.extend([min(limit, 200), max(offset, 0)])
    cursor.execute(fetch_sql, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    events = []
    for r in rows:
        d = dict(r)
        if d.get("details"):
            try:
                d["details"] = json.loads(d["details"])
            except Exception:
                pass
        events.append(d)

    return events, total_count


class CentralizedAuditService:
    @staticmethod
    def record_event(
        tenant_id: str,
        event_type: str,
        actor_id: str,
        actor_type: str = "user",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
        payload_hash: Optional[str] = None
    ) -> str:
        return record_audit_event(
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            metadata=metadata,
            payload_hash=payload_hash
        )

    @staticmethod
    def query_events(
        tenant_id: str,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        return query_audit_logs(
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            search_query=search_query,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset
        )


