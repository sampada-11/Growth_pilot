"""
Pydantic Schemas for Experiments Engine (§8.5, §9.5, FR-046 to FR-053).
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ExperimentCreateSchema(BaseModel):
    campaign_id: str = Field(..., description="ID of the campaign to evaluate")
    holdout_pct: float = Field(20.0, ge=1.0, le=50.0, description="Percentage of audience reserved as control holdout (1% to 50%)")
    start_at: Optional[str] = Field(None, description="ISO timestamp for start of experiment")
    end_at: Optional[str] = Field(None, description="ISO timestamp for scheduled end of experiment")


class ExperimentEvaluateSchema(BaseModel):
    end_experiment: bool = Field(True, description="Whether to finalize experiment and transition opportunity")
    force_simulate: bool = Field(False, description="Force running seeded demo simulation")


class ArmMetrics(BaseModel):
    arm: str
    customers: int
    conversions: int
    conversion_rate: float
    revenue: float
    revenue_per_customer: float
    aov: float
    spend: float
    profit: float


class UpliftMetrics(BaseModel):
    conversion_lift_abs: float
    conversion_lift_rel: float
    revenue_per_customer_lift: float
    incremental_revenue: float
    incremental_profit: float


class ConfidenceInterval(BaseModel):
    lower: float
    upper: float


class ZTestResult(BaseModel):
    z_score: float
    p_value: float
    ci_95: ConfidenceInterval
    significant: bool


class TTestResult(BaseModel):
    t_stat: float
    p_value: float
    df: float
    ci_95: ConfidenceInterval
    significant: bool


class SampleSizeCheck(BaseModel):
    passed: bool
    min_sample_per_arm: int
    min_conversions_per_arm: int
    control_customers: int
    treatment_customers: int
    control_conversions: int
    treatment_conversions: int
    control_progress_pct: float
    treatment_progress_pct: float
    status: str


class ExperimentDetailSchema(BaseModel):
    experiment_id: str
    tenant_id: str
    campaign_id: str
    holdout_pct: float
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    status: str
    verdict: Optional[str] = None
    is_simulated: bool
    control_customers: int = 0
    treatment_customers: int = 0
    created_at: str


class ExperimentResultSchema(BaseModel):
    experiment_id: str
    tenant_id: str
    campaign_id: str
    status: str
    verdict: str
    verdict_reason: str
    is_simulated: bool
    control: ArmMetrics
    treatment: ArmMetrics
    uplift: UpliftMetrics
    z_test: ZTestResult
    welch_t_test: TTestResult
    sample_size_check: SampleSizeCheck
    next_experiment_recommendation: Optional[Dict[str, Any]] = None
    learning_signal: Optional[Dict[str, Any]] = None
    opportunity_transition: Optional[Dict[str, Any]] = None
    evaluated_at: str

