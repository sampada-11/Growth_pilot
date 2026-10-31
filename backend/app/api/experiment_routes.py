"""
Experiments Engine Endpoints (§13, FR-046 to FR-053).
Mounted at /api/v1/experiments.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from backend.app.auth.dependencies import get_current_user, get_current_tenant
from backend.app.experiments.service import (
    ExperimentService,
    ExperimentException,
    ExperimentNotFoundException,
    CampaignNotFoundForExperimentException
)
from backend.app.experiments.schemas import (
    ExperimentCreateSchema,
    ExperimentEvaluateSchema,
    ExperimentDetailSchema,
    ExperimentResultSchema
)

router = APIRouter(prefix="/api/v1/experiments", tags=["Experiments"])


def handle_experiment_exception(e: ExperimentException):
    raise HTTPException(
        status_code=e.status_code,
        detail={"error": {"code": e.code, "message": e.message, **e.details}}
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_experiment(
    payload: ExperimentCreateSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Creates an experiment from a campaign with configurable holdout (FR-046).
    Performs deterministic customer assignment (FR-047).
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    try:
        return ExperimentService.create_experiment(
            tenant_id=tenant_id,
            payload=payload.model_dump(exclude_unset=True),
            actor_id=actor_id
        )
    except ExperimentException as e:
        handle_experiment_exception(e)


@router.get("", response_model=List[Dict[str, Any]])
def list_experiments(
    campaign_id: Optional[str] = Query(None, description="Filter experiments by campaign ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Lists all experiments for current tenant.
    """
    return ExperimentService.list_experiments(tenant_id=tenant_id, campaign_id=campaign_id)


@router.get("/{experiment_id}", response_model=Dict[str, Any])
def get_experiment_detail(
    experiment_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Retrieves experiment details and arm counts (control vs treatment).
    """
    try:
        return ExperimentService.get_experiment_detail(tenant_id=tenant_id, experiment_id=experiment_id)
    except ExperimentException as e:
        handle_experiment_exception(e)


@router.post("/{experiment_id}/evaluate", response_model=Dict[str, Any])
def evaluate_experiment(
    experiment_id: str,
    payload: Optional[ExperimentEvaluateSchema] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Runs statistical evaluation, applies winner decision rules,
    records learning signals, and transitions linked opportunity (FR-048 to FR-053).
    """
    actor_id = current_user.get("user_id") or current_user.get("sub") or "user"
    end_experiment = payload.end_experiment if payload else True
    force_simulate = payload.force_simulate if payload else False
    try:
        return ExperimentService.evaluate_experiment(
            tenant_id=tenant_id,
            experiment_id=experiment_id,
            actor_id=actor_id,
            end_experiment=end_experiment,
            force_simulate=force_simulate
        )
    except ExperimentException as e:
        handle_experiment_exception(e)


@router.get("/{experiment_id}/results", response_model=Dict[str, Any])
def get_experiment_results(
    experiment_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Retrieves statistical evaluation results (z-test, Welch t-test, CIs, winner verdict).
    """
    try:
        return ExperimentService.get_experiment_results(tenant_id=tenant_id, experiment_id=experiment_id)
    except ExperimentException as e:
        handle_experiment_exception(e)

