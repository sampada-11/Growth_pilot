"""
Campaign Studio Endpoints (§13, FR-032 to FR-045)
Mounted at /api/v1/campaigns.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from backend.app.auth.dependencies import get_current_user, get_current_tenant
from backend.app.campaigns.service import (
    CampaignService,
    CampaignException,
    CampaignNotFoundException,
    CampaignNotApprovedException,
    LiveAdapterUnavailableException,
    CampaignGuardrailBlockedException,
    CampaignInsufficientRoleException
)
from backend.app.campaigns.schemas import (
    CampaignCreateSchema,
    GenerateContentRequestSchema,
    CampaignApproveSchema,
    CampaignScheduleSchema,
    CampaignExecuteSchema
)

router = APIRouter(prefix="/api/v1/campaigns", tags=["Campaigns"])


def handle_campaign_exception(e: CampaignException):
    raise HTTPException(
        status_code=e.status_code,
        detail={"error": {"code": e.code, "message": e.message, **e.details}}
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_campaign(
    payload: CampaignCreateSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Creates a new campaign from an approved opportunity or manually (FR-032).
    Generates 3 email and 3 push AI copy variants (FR-035).
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    try:
        return CampaignService.create_campaign(
            tenant_id=tenant_id,
            payload=payload.model_dump(exclude_unset=True),
            actor_id=actor_id
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.get("", response_model=List[Dict[str, Any]])
def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status (draft, approved, scheduled, completed)"),
    objective: Optional[str] = Query(None, description="Filter by objective enum"),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant)
):
    """Lists campaigns for the authenticated tenant."""
    try:
        return CampaignService.list_campaigns(
            tenant_id=tenant_id,
            status=status,
            objective=objective,
            limit=limit
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.get("/channels/readiness", response_model=Dict[str, Any])
def get_channel_readiness(
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Returns channel operational readiness for Demo Mode vs Live Mode (§9.4, FR-041, FR-042).
    Strict constraint: Do not show unsupported channel integrations as operational.
    """
    try:
        return CampaignService.get_channel_readiness(tenant_id=tenant_id)
    except CampaignException as e:
        handle_campaign_exception(e)


@router.get("/{id}", response_model=Dict[str, Any])
def get_campaign_detail(
    id: str,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns campaign detail with all content variants and delivery summary."""
    try:
        return CampaignService.get_campaign_detail(tenant_id=tenant_id, campaign_id=id)
    except CampaignException as e:
        handle_campaign_exception(e)


@router.post("/{id}/generate-content")
def generate_campaign_content(
    id: str,
    payload: Optional[GenerateContentRequestSchema] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Generates or regenerates 3 email + 3 push AI content variants with deterministic linter (FR-035).
    """
    prod_id = payload.product_id if payload else None
    disc_pct = payload.discount_pct if payload else None
    try:
        return CampaignService.generate_content_variants(
            tenant_id=tenant_id,
            campaign_id=id,
            product_id=prod_id,
            discount_pct=disc_pct
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.get("/{id}/preview")
def preview_campaign(
    id: str,
    customer_id: Optional[str] = Query(None, description="Optional sample customer ID for token resolution"),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Renders email and push previews with personalization tokens resolved from sample customer (FR-036).
    """
    try:
        return CampaignService.preview_campaign(
            tenant_id=tenant_id,
            campaign_id=id,
            customer_id=customer_id
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.post("/{id}/approve")
def approve_campaign(
    id: str,
    payload: Optional[CampaignApproveSchema] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Approves a campaign draft for execution (FR-029, FR-039).
    Requires role 'owner', 'admin', 'marketing_manager', or 'growth_manager'.
    Enforces guardrail evaluation before approval.
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    actor_role = current_user.get("role") or "growth_manager"
    note = payload.note if payload else "Approved campaign execution"
    try:
        return CampaignService.approve_campaign(
            tenant_id=tenant_id,
            campaign_id=id,
            actor_id=actor_id,
            actor_role=actor_role,
            note=note
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.post("/{id}/schedule")
def schedule_campaign(
    id: str,
    payload: CampaignScheduleSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """Schedules campaign execution (FR-040)."""
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    try:
        return CampaignService.schedule_campaign(
            tenant_id=tenant_id,
            campaign_id=id,
            send_now=payload.send_now,
            scheduled_at=payload.scheduled_at,
            tz=payload.timezone,
            actor_id=actor_id
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.post("/{id}/execute", status_code=status.HTTP_202_ACCEPTED)
def execute_campaign(
    id: str,
    payload: CampaignExecuteSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Executes a campaign (FR-041 to FR-045).
    - Returns 409 NOT_APPROVED if campaign is still in draft.
    - Returns 422 LIVE_ADAPTER_UNAVAILABLE if live mode requested without credentials.
    - Gated by immediate pre-execution Guardrail validation.
    - Enforces idempotency key per customer + channel.
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    try:
        return CampaignService.execute_campaign(
            tenant_id=tenant_id,
            campaign_id=id,
            mode=payload.mode,
            actor_id=actor_id
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.get("/{id}/deliveries")
def get_campaign_deliveries(
    id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns delivery event logs (FR-043)."""
    try:
        return CampaignService.get_campaign_deliveries(
            tenant_id=tenant_id,
            campaign_id=id,
            limit=limit,
            offset=offset
        )
    except CampaignException as e:
        handle_campaign_exception(e)


@router.get("/{id}/performance")
def get_campaign_performance(
    id: str,
    tenant_id: str = Depends(get_current_tenant)
):
    """Returns aggregate performance analytics (FR-044)."""
    try:
        return CampaignService.get_campaign_performance(
            tenant_id=tenant_id,
            campaign_id=id
        )
    except CampaignException as e:
        handle_campaign_exception(e)

