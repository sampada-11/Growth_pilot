"""
Pydantic Schemas for GrowthPilot Conversational Copilot.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CopilotMetricItem(BaseModel):
    label: str
    value: str
    subtext: Optional[str] = None
    delta: Optional[str] = None
    status: Optional[str] = "neutral"  # 'positive', 'negative', 'warning', 'neutral'


class CopilotSuggestedAction(BaseModel):
    label: str
    action_type: str  # 'navigate_tab', 'launch_studio', 'view_opportunity', 'trigger_query'
    target_tab: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    button_style: Optional[str] = "primary"  # 'primary', 'secondary', 'warning'


class CopilotGuardrailCard(BaseModel):
    status: str  # 'passed', 'warning', 'blocked'
    policy_name: str
    checks: List[Dict[str, Any]] = Field(default_factory=list)
    requires_approval: bool = True
    execution_blocked: bool = True
    rationale: str


class CopilotChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    context_filters: Optional[Dict[str, Any]] = None


class CopilotChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    question: str
    intent: str
    intent_label: str
    answer: str
    metrics: List[CopilotMetricItem] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = None
    guardrail_status: Optional[CopilotGuardrailCard] = None
    suggested_actions: List[CopilotSuggestedAction] = Field(default_factory=list)
    is_simulated: bool = True
    created_at: str


class QuickPromptItem(BaseModel):
    id: str
    prompt: str
    category: str
    icon: str

