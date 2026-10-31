"""
Unified LLM Client Wrapper (Module B — FR-020, FR-022)
Provides resilient AI inference with:
- 30-second timeout, 2 retries
- LLM_MODE=live|mock configuration
- Structured JSON and Pydantic parsing
- Strict 'is_simulated=true' labeling in mock mode
- Zero financial calculation hallucination (text content only)
- Audit event logging for every LLM invocation
"""
import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel

from backend.app.audit.service import record_audit_event

T = TypeVar("T", bound=BaseModel)

LLM_MODE = os.environ.get("LLM_MODE", "mock").lower() # 'live' or 'mock'
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
MAX_RETRIES = 2


class LLMResponse(BaseModel):
    content: str
    parsed_json: Optional[Dict[str, Any]] = None
    is_simulated: bool = True
    model: str = "mock-agent-engine-v1"
    latency_ms: int = 0
    tokens_used: int = 0


def generate_llm_response(
    prompt: str,
    system_instruction: str = "You are GrowthPilot AI, an autonomous e-commerce growth strategist. Output valid JSON.",
    schema_cls: Optional[Type[T]] = None,
    tenant_id: str = "tenant_store_alpha",
    agent_name: str = "GrowthStrategyAgent"
) -> LLMResponse:
    """
    Unified entrypoint for all agent LLM calls.
    Enforces timeout, retries, multi-tenant prompt hygiene, and audit logging.
    """
    start_time = time.time()
    input_hash = hashlib.sha256((system_instruction + prompt).encode()).hexdigest()[:16]

    is_simulated = (LLM_MODE != "live" or not GEMINI_API_KEY)
    response_text = ""
    parsed_data = None
    tokens_used = 0
    attempts = 0
    last_error = None

    while attempts <= MAX_RETRIES:
        attempts += 1
        try:
            if not is_simulated:
                # Live Gemini API call
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=GEMINI_API_KEY)
                    model = genai.GenerativeModel(
                        model_name=LLM_MODEL,
                        system_instruction=system_instruction
                    )
                    res = model.generate_content(
                        prompt,
                        request_options={"timeout": TIMEOUT_SECONDS}
                    )
                    response_text = res.text
                    tokens_used = getattr(res, "usage_metadata", {}).total_token_count if hasattr(res, "usage_metadata") else 150
                    break
                except Exception as err:
                    last_error = err
                    if attempts > MAX_RETRIES:
                        # Fallback to deterministic mock mode on live exhaustion
                        is_simulated = True
                        break
                    time.sleep(0.5)
            else:
                # Deterministic Mock Engine
                response_text = _generate_mock_output(agent_name, prompt, tenant_id)
                tokens_used = len(prompt.split()) + 80
                break
        except Exception as err:
            last_error = err
            if attempts > MAX_RETRIES:
                break
            time.sleep(0.5)

    if not response_text and is_simulated:
        response_text = _generate_mock_output(agent_name, prompt, tenant_id)

    # Attempt to parse JSON if schema or structured output is expected
    try:
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        parsed_data = json.loads(clean_text)
    except Exception:
        parsed_data = None

    latency_ms = int((time.time() - start_time) * 1000)

    # FR-020: Every agent invocation writes an audit event
    record_audit_event(
        tenant_id=tenant_id,
        event_type="agent.step_completed",
        actor_id=agent_name,
        actor_type="agent",
        entity_type="llm_invocation",
        entity_id=input_hash,
        status="success" if response_text else "failed",
        metadata={
            "agent": agent_name,
            "is_simulated": is_simulated,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "attempts": attempts,
            "model": LLM_MODEL if not is_simulated else "mock-agent-engine-v1"
        }
    )

    return LLMResponse(
        content=response_text,
        parsed_json=parsed_data,
        is_simulated=is_simulated,
        model=LLM_MODEL if not is_simulated else "mock-agent-engine-v1",
        latency_ms=latency_ms,
        tokens_used=tokens_used
    )


def _generate_mock_output(agent_name: str, prompt: str, tenant_id: str) -> str:
    """
    Deterministic domain-grounded mock text generator.
    Produces valid JSON adhering to PRD requirements for SoundWave Audio (A) and PulseWear (B).
    """
    if "customer" in agent_name.lower():
        if tenant_id == "tenant_store_alpha":
            return json.dumps({
                "retention_suggestions": [
                    {
                        "segment_id": "seg_18_25",
                        "text": "Young Adults (18-25) exhibit high checkout drop-off on accessory add-ons. Deploy SMS/Push reminders with limited-time bundling."
                    },
                    {
                        "segment_id": "seg_champions",
                        "text": "Champions cohort purchasing Earbuds Pro have high CLV; offer early access to audio charging accessories."
                    }
                ]
            })
        else:
            return json.dumps({
                "retention_suggestions": [
                    {
                        "segment_id": "seg_runners",
                        "text": "Marathon Runners inactive for >90 days require proactive heart-rate strap win-back sequence."
                    }
                ]
            })

    elif "product" in agent_name.lower():
        return json.dumps({
            "problem_narratives": [
                {
                    "product_id": "PROD-002",
                    "narrative": "Charging Stand demonstrates severe checkout friction despite high add-to-cart velocity among entry-level earbud buyers."
                }
            ]
        })

    elif "strategy" in agent_name.lower():
        if tenant_id == "tenant_store_alpha":
            return json.dumps({
                "title": "Earbud Stand Checkout Drop-off Recovery",
                "description": "High cart abandonment (71%) detected for Earbud Case & Charging Stand (PROD-002) among Young Adult Earbud owners.",
                "root_cause_narrative": "Telemetry indicates customer hesitation at OTP/payment threshold due to accessory price sensitivity following primary earbud purchase.",
                "hypotheses": [
                    {
                        "text": "Accessory price point perceived as high immediately after core hardware purchase.",
                        "evidence_refs": ["funnel.checkout_started", "products.PROD-002.abandonment_rate"],
                        "strength": "high"
                    }
                ]
            })
        else:
            return json.dumps({
                "title": "Marathon Runner VIP Inactivity Win-Back",
                "description": "65% 90-day inactivity detected among high-value smartwatch customers.",
                "root_cause_narrative": "Runners complete target training cycles and disengage from store ecosystem without accessory triggers.",
                "hypotheses": [
                    {
                        "text": "Lack of training sensor accessory integration leads to app and store drop-off.",
                        "evidence_refs": ["customers.churn_risk", "products.PROD-B03.velocity"],
                        "strength": "high"
                    }
                ]
            })

    elif "campaign" in agent_name.lower():
        pct = 8
        return json.dumps({
            "email_variants": [
                {
                    "subject": f"Complete your setup: {pct}% off Earbud Stand",
                    "preheader": "Keep your earbuds charged and ready for every beat.",
                    "body": f"We noticed you left the Earbud Stand in your cart. Claim your exclusive {pct}% discount today.",
                    "cta": "Claim My Offer"
                },
                {
                    "subject": f"Your special {pct}% discount is waiting",
                    "preheader": "Exclusive VIP offer on the Earbud Charging Stand.",
                    "body": f"Take your audio experience to the next level with {pct}% off the Earbud Charging Stand.",
                    "cta": "Unlock 8% Savings"
                },
                {
                    "subject": f"Don't miss out: {pct}% off Charging Stand",
                    "preheader": "Limited time VIP pricing for audio enthusiasts.",
                    "body": f"Your earbuds deserve the best home. Save {pct}% on the charging stand today.",
                    "cta": "Shop Now"
                }
            ],
            "push_variants": [
                {
                    "title": f"Complete your audio setup — {pct}% Off",
                    "body": f"Your Earbud Charging Stand is waiting! Enjoy {pct}% off at checkout today."
                },
                {
                    "title": f"Special Offer: {pct}% Off Earbud Stand",
                    "body": f"VIP access: Get {pct}% off your charging stand. Limited time only."
                },
                {
                    "title": "Left something behind?",
                    "body": f"Grab your Earbud Stand now with an exclusive {pct}% discount."
                }
            ]
        })

    return json.dumps({"status": "ok", "message": "Standard agent generated response."})

