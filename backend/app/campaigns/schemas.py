"""
Campaign Studio Schemas (§8.4, FR-032 to FR-045)
Pydantic schemas for campaign drafts, AI copy generation, scheduling, and execution.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


VALID_OBJECTIVES = [
    "recover_abandoned_carts",
    "reactivate_inactive",
    "retain_high_value",
    "promote_product",
    "bundle_upsell"
]


class CampaignCreateSchema(BaseModel):
    opportunity_id: Optional[str] = None
    name: Optional[str] = None
    objective: str = Field("recover_abandoned_carts", description="Campaign objective enum")
    segment_id: Optional[str] = None
    mode: str = Field("demo", description="demo or live")
    discount: Optional[Dict[str, Any]] = None
    budget_total: float = Field(0.0, ge=0.0)
    per_customer_cap: float = Field(1.0, ge=0.0)
    audience_size: Optional[int] = Field(None, ge=1, description="Target audience size")
    channels: Optional[List[str]] = Field(default_factory=lambda: ["email", "push"])


class GenerateContentRequestSchema(BaseModel):
    product_id: Optional[str] = None
    discount_pct: Optional[float] = None
    tone: Optional[str] = "compelling"


class CampaignApproveSchema(BaseModel):
    note: Optional[str] = "Approved campaign execution"


class CampaignScheduleSchema(BaseModel):
    send_now: bool = True
    scheduled_at: Optional[str] = None
    timezone: str = "Asia/Kolkata"


class CampaignExecuteSchema(BaseModel):
    mode: str = Field("demo", description="demo or live")


class ContentVariantUpdateSchema(BaseModel):
    channel: str
    variant: str
    subject: Optional[str] = None
    preheader: Optional[str] = None
    body: str
    cta: str

