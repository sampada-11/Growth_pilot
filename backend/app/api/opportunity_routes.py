"""
Growth Opportunities Endpoints (§13, FR-023 to FR-031)
Mounted at /api/v1/opportunities.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from backend.app.auth.dependencies import get_current_user, get_current_tenant
from backend.app.opportunities.service import (
    OpportunityService,
    OpportunityException,
    InvalidTransitionException,
    InsufficientRoleException,
    GuardrailBlockedException,
    MissingReasonException,
    OpportunityNotFoundException
)
from backend.app.opportunities.schemas import (
    StrategyUpdateSchema,
    ApproveRequestSchema,
    RejectRequestSchema,
    TransitionStateRequestSchema
)

router = APIRouter(prefix="/api/v1/opportunities", tags=["Opportunities"])


def handle_service_exception(e: OpportunityException):
    raise HTTPException(
        status_code=e.status_code,
        detail={"error": {"code": e.code, "message": e.message, **e.details}}
    )


@router.get("", response_model=List[Dict[str, Any]])
def list_opportunities(
    status: Optional[str] = Query(None, description="Filter by status or lifecycle_state"),
    risk: Optional[str] = Query(None, description="Filter by risk_level (low, medium, high)"),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Returns opportunities ranked by priority score (Section 16.2),
    filterable by lifecycle state and risk level.
    """
    try:
        return OpportunityService.list_opportunities(
            tenant_id=tenant_id,
            status=status,
            risk=risk,
            limit=limit
        )
    except OpportunityException as e:
        handle_service_exception(e)


@router.get("/analytics", response_model=Dict[str, Any])
def get_opportunities_analytics(
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Returns aggregated opportunity metrics:
    - Summary (total opportunities, pipeline revenue, average priority)
    - Category distribution (counts, revenue, percentages)
    - Revenue potential comparison series
    - Ranked opportunities
    """
    try:
        return OpportunityService.get_opportunities_analytics(tenant_id=tenant_id)
    except OpportunityException as e:
        handle_service_exception(e)


@router.get("/{id}", response_model=Dict[str, Any])
def get_opportunity_detail(
    id: str,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Returns full opportunity detail including problem statement, root cause hypotheses,
    affected customers, supporting analytics, deterministic impact inputs, guardrails, and audit history.
    """
    try:
        return OpportunityService.get_opportunity_detail(tenant_id=tenant_id, opportunity_id=id)
    except OpportunityException as e:
        handle_service_exception(e)


@router.patch("/{id}/strategy", response_model=Dict[str, Any])
def edit_opportunity_strategy(
    id: str,
    payload: StrategyUpdateSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Edits commercial strategy (discount %, channel, audience size).
    Dynamically recalculates financial impact and re-runs Guardrail Agent before approval can be granted.
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    try:
        return OpportunityService.update_strategy(
            tenant_id=tenant_id,
            opportunity_id=id,
            strategy_update=payload.model_dump(exclude_unset=True),
            actor_id=actor_id
        )
    except OpportunityException as e:
        handle_service_exception(e)


@router.post("/{id}/approve")
def approve_opportunity(
    id: str,
    payload: Optional[ApproveRequestSchema] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Approves an opportunity for campaign staging and execution.
    Requires role 'owner', 'admin', or 'marketing_manager' / 'growth_manager'.
    Validates state transition and passes through Guardrail re-check.
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    actor_role = current_user.get("role") or "growth_manager"
    note = payload.note if payload else "Approved for execution"

    try:
        return OpportunityService.approve_opportunity(
            tenant_id=tenant_id,
            opportunity_id=id,
            actor_id=actor_id,
            actor_role=actor_role,
            note=note
        )
    except OpportunityException as e:
        handle_service_exception(e)


@router.post("/{id}/reject")
def reject_opportunity(
    id: str,
    payload: RejectRequestSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Rejects an opportunity. Requires a mandatory rejection reason.
    Transitions state to 'rejected' and logs to immutable audit trail.
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    actor_role = current_user.get("role") or "growth_manager"

    try:
        return OpportunityService.reject_opportunity(
            tenant_id=tenant_id,
            opportunity_id=id,
            actor_id=actor_id,
            actor_role=actor_role,
            reason=payload.reason,
            note=payload.note
        )
    except OpportunityException as e:
        handle_service_exception(e)


@router.post("/{id}/transition")
def transition_opportunity_state(
    id: str,
    payload: TransitionStateRequestSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Executes a lifecycle state transition (e.g., executing -> completed).
    Illegal transitions return HTTP 409.
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "system"
    try:
        return OpportunityService.transition_state(
            tenant_id=tenant_id,
            opportunity_id=id,
            to_state=payload.to_state,
            actor_id=actor_id,
            reason=payload.reason
        )
    except OpportunityException as e:
        handle_service_exception(e)
