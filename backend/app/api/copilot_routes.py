"""
Conversational Copilot API Routes.
Mounted at /api/v1/copilot.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status

from backend.app.auth.dependencies import get_current_user, get_current_tenant
from backend.app.copilot.service import CopilotService
from backend.app.copilot.schemas import (
    CopilotChatRequest,
    CopilotChatResponse,
    QuickPromptItem
)

router = APIRouter(prefix="/api/v1/copilot", tags=["Copilot"])


@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(
    payload: CopilotChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Submits a natural-language question to the GrowthPilot Copilot.
    Resolves intent, queries tenant-specific analytics, evaluates safety guardrails,
    and returns an executive explanation with figures, evidence, and suggested actions.
    """
    user_id = current_user.get("user_id") or current_user.get("sub") or "user"
    return CopilotService.process_query(
        tenant_id=tenant_id,
        user_id=user_id,
        question=payload.question,
        conversation_id=payload.conversation_id
    )


@router.get("/quick-prompts", response_model=List[QuickPromptItem])
def get_quick_prompts():
    """Returns curated 1-click prompt suggestions for hackathon demonstration."""
    return CopilotService.get_quick_prompts()


@router.get("/history", response_model=List[Dict[str, Any]])
def get_conversation_history(
    conversation_id: Optional[str] = Query(None, description="Optional conversation ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """Retrieves conversation message history for the active tenant."""
    return CopilotService.get_conversation_history(tenant_id=tenant_id, conversation_id=conversation_id)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_conversation_history(
    conversation_id: Optional[str] = Query(None, description="Optional conversation ID to reset"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    """Resets copilot conversation history for demonstration."""
    CopilotService.clear_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
    return None

