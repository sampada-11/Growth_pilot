"""
Agent Orchestration API Routes (Module B — FR-011, FR-019, FR-021)
Base path: /api/v1/agents/* and /api/v1/guardrails/*
"""
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.app.auth.dependencies import get_current_tenant
from backend.app.agents.orchestrator import orchestrate_analysis_pipeline
from backend.app.agents.guardrail_agent import evaluate_guardrails
from backend.app.db.models import get_db_connection

router = APIRouter(tags=["agents"])


@router.post("/api/v1/agents/runs")
def start_analysis_run(
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """Triggers autonomous multi-agent analysis run: (Customer ∥ Product) → Strategy → Guardrail → Campaign."""
    try:
        result = orchestrate_analysis_pipeline(tenant_id=tenant_id)
        return result
    except Exception as err:
        raise HTTPException(status_code=500, detail={"error": "AGENT_RUN_FAILED", "message": str(err)})


@router.get("/api/v1/agents/runs")
def list_agent_runs(
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant)
):
    """Lists past agent execution runs for the tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM agent_runs 
        WHERE tenant_id = ? 
        ORDER BY created_at DESC LIMIT ?
    """, (tenant_id, limit))
    rows = cursor.fetchall()
    conn.close()

    runs = []
    for r in rows:
        d = dict(r)
        if d.get("summary"):
            try:
                d["summary"] = json.loads(d["summary"])
            except Exception:
                pass
        runs.append(d)
    return runs


@router.get("/api/v1/agents/runs/{id}")
def get_agent_run_detail(
    id: str,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns status, metadata, and step breakdown for an agent run."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_runs WHERE run_id = ? AND tenant_id = ?", (id, tenant_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Agent run '{id}' not found for tenant '{tenant_id}'.")

    run_dict = dict(row)
    if run_dict.get("summary"):
        try:
            run_dict["summary"] = json.loads(run_dict["summary"])
        except Exception:
            pass

    cursor.execute("""
        SELECT * FROM agent_steps 
        WHERE run_id = ? AND tenant_id = ? 
        ORDER BY created_at ASC
    """, (id, tenant_id))
    step_rows = cursor.fetchall()
    conn.close()

    steps = []
    for s in step_rows:
        sd = dict(s)
        for field in ["input_data", "output_data"]:
            if sd.get(field):
                try:
                    sd[field] = json.loads(sd[field])
                except Exception:
                    pass
        steps.append(sd)

    run_dict["steps"] = steps
    return run_dict


@router.post("/api/v1/guardrails/validate")
def dry_run_guardrails(
    payload: Dict[str, Any],
    tenant_id: str = Depends(get_current_tenant)
):
    """Dry-run validation endpoint for evaluating proposed campaigns against rules GR-01 to GR-09."""
    result = evaluate_guardrails(
        proposal=payload,
        tenant_id=tenant_id
    )
    return result.model_dump()

