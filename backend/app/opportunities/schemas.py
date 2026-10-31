"""
Opportunities Schemas (§9.3, FR-023 to FR-031)
Pydantic schemas for Opportunity Lifecycle and Strategy Editing.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class StrategyUpdateSchema(BaseModel):
    type: Optional[str] = None
    discount_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    channel: Optional[str] = None
    channels: Optional[List[str]] = None
    audience_size: Optional[int] = Field(None, ge=1)
    duration_days: Optional[int] = None
    note: Optional[str] = None


class ApproveRequestSchema(BaseModel):
    note: Optional[str] = "Approved for execution"


class RejectRequestSchema(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory reason for rejection")
    note: Optional[str] = None


class TransitionStateRequestSchema(BaseModel):
    to_state: str
    reason: Optional[str] = None

