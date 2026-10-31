"""
Pydantic Schemas for Multi-Agent System (Module B — FR-012, §11)
Defines strict input and output data contracts for CIA, PIA, GSA, GRA, and CEA.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Common Agent Envelope (§11.1)
# -------------------------------------------------------------------------

class BaseAgentOutput(BaseModel):
    agent: str
    run_id: str
    tenant_id: str
    generated_at: str
    status: str = "success" # 'success', 'failed', 'partial_evidence'
    warnings: List[str] = Field(default_factory=list)
    is_simulated: bool = False
    llm_used: bool = False
    data: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------------------
# 1. Customer Intelligence Agent (§11.2)
# -------------------------------------------------------------------------

class CustomerSegmentItem(BaseModel):
    id: str
    name: str
    size: int
    definition: Dict[str, Any]


class RFMItem(BaseModel):
    customer_id: str
    R: int # 1-5
    F: int # 1-5
    M: int # 1-5
    segment: str


class ChurnRiskItem(BaseModel):
    customer_id: str
    score: float # 0.0 - 1.0
    reasons: List[str]
    method: str # 'heuristic' or 'model'


class HighValueCustomerItem(BaseModel):
    customer_id: str
    total_spend: float
    order_count: int


class RetentionSuggestion(BaseModel):
    segment_id: str
    text: str


class CustomerAgentData(BaseModel):
    segments: List[CustomerSegmentItem] = Field(default_factory=list)
    rfm: List[RFMItem] = Field(default_factory=list)
    churn_risk: List[ChurnRiskItem] = Field(default_factory=list)
    high_value: List[HighValueCustomerItem] = Field(default_factory=list)
    inactive: List[Dict[str, Any]] = Field(default_factory=list)
    retention_suggestions: List[RetentionSuggestion] = Field(default_factory=list)


# -------------------------------------------------------------------------
# 2. Product Intelligence Agent (§11.3)
# -------------------------------------------------------------------------

class ProductRankingItem(BaseModel):
    product_id: str
    name: str
    revenue: float
    units: int
    trend_slope: float


class ProblemProductItem(BaseModel):
    product_id: str
    issue: str # e.g. 'high_cart_abandonment', 'high_return_rate'
    metric: str
    value: float
    segment_breakdown: Dict[str, Any] = Field(default_factory=dict)


class BundleCandidateItem(BaseModel):
    product_a: str
    product_b: str
    support_orders: int
    product_a_name: Optional[str] = None
    product_b_name: Optional[str] = None


class ProductAgentData(BaseModel):
    ranking: List[ProductRankingItem] = Field(default_factory=list)
    problem_products: List[ProblemProductItem] = Field(default_factory=list)
    return_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    inventory_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    bundles: List[BundleCandidateItem] = Field(default_factory=list)


# -------------------------------------------------------------------------
# 3. Guardrail Agent (§11.6 & §23)
# -------------------------------------------------------------------------

class RuleEvaluation(BaseModel):
    id: str # 'GR-01', 'GR-02', etc.
    name: str
    passed: bool
    observed: Any
    limit: Any
    message: str


class GuardrailOutput(BaseModel):
    decision: str # 'ALLOW', 'REQUIRE_APPROVAL', 'BLOCK'
    risk_tier: str # 'Low', 'Medium', 'High', 'Blocked' (backward-compatible)
    status: str # 'Allowed', 'Requires Approval', 'Blocked'
    rules: List[RuleEvaluation]
    reasons: List[str]
    evaluated_at: str
    can_auto_execute: bool = False
    requires_approval: bool = False
    requires_justification: bool = False
    discount_band: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------------------
# 4. Growth Strategy Agent (§11.4 & §9.3)
# -------------------------------------------------------------------------

class HypothesisItem(BaseModel):
    text: str
    evidence_refs: List[str]
    strength: str = "high"


class OpportunityStrategy(BaseModel):
    type: str # 'targeted_discount', 'vip_winback', 'bundle_upsell'
    discount_pct: float
    channels: List[str] = Field(default_factory=lambda: ["email", "push"])
    audience_segment: str
    duration_days: int = 7


class OpportunityItem(BaseModel):
    opportunity_id: str
    tenant_id: str
    title: str
    description: str
    problem: str
    root_cause: Dict[str, Any] # {hypotheses: [...]}
    affected_customers: Dict[str, Any] # {count: int, segment_id: str, definition: dict}
    product_id: Optional[str] = None
    supporting_analytics: Dict[str, Any] = Field(default_factory=dict)
    strategy: OpportunityStrategy
    expected_impact: float # backward-compatible
    est_revenue_impact: float
    est_profit_impact: float
    confidence: float # 0.0 - 1.0
    urgency_factor: float = 1.0
    priority_score: float # 0 - 100 or weighted
    priority_rank: int = 1
    risk_level: str = "medium"
    approval_status: str = "pending"
    execution_status: str = "not_started"
    lifecycle_state: str = "detected" # 'detected', 'analysed', 'pending_approval', 'approved', etc.
    guardrail_result: Optional[Dict[str, Any]] = None
    impact_inputs: Optional[Dict[str, Any]] = None
    recommended_action: Optional[str] = None # backward-compatible
    status: str = "open" # backward-compatible
    created_at: Optional[str] = None


# -------------------------------------------------------------------------
# 5. Campaign Execution Agent (§11.5)
# -------------------------------------------------------------------------

class EmailVariant(BaseModel):
    subject: str
    preheader: str
    body: str
    cta: str


class PushVariant(BaseModel):
    title: str
    body: str


class CampaignContentOutput(BaseModel):
    email_variants: List[EmailVariant]
    push_variants: List[PushVariant]
    lint_passed: bool = True
    lint_errors: List[str] = Field(default_factory=list)


class CampaignDraftOutput(BaseModel):
    campaign_id: str
    tenant_id: str
    opportunity_id: Optional[str] = None
    target_segment: str
    product_id: Optional[str] = None
    offer_pct: float
    discount_band: Dict[str, Any]
    content: CampaignContentOutput
    guardrail: GuardrailOutput
    expected_roi: float
    status: str = "drafted"
    created_at: str

