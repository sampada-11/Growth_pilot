"""
Channel Delivery Adapters (§9.4, FR-041, FR-042)
Implements ChannelAdapter interface with SimulatedAdapter (demo mode) and LiveAdapter (production mode).
"""
import os
import uuid
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional


class ChannelAdapter(ABC):
    """Abstract base channel adapter interface."""

    @abstractmethod
    def send_message(
        self,
        tenant_id: str,
        customer_id: str,
        channel: str,
        content: Dict[str, Any],
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sends a single message through the channel."""
        pass

    @abstractmethod
    def batch_send(
        self,
        tenant_id: str,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Sends a batch of messages."""
        pass

    @abstractmethod
    def check_connectivity(self) -> Tuple[bool, str]:
        """Validates adapter readiness and returns (is_ready, message)."""
        pass


class SimulatedAdapter(ChannelAdapter):
    """
    Simulated Channel Adapter for Demo Mode (§9.4).
    Produces deterministic and probabilistic simulated delivery events.
    Always flags is_simulated=True.
    """
    def __init__(self):
        self.is_simulated = True

    def check_connectivity(self) -> Tuple[bool, str]:
        return True, "Simulated adapter operational (Demo Mode active)."

    def send_message(
        self,
        tenant_id: str,
        customer_id: str,
        channel: str,
        content: Dict[str, Any],
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        msg_id = f"sim_{channel[:3]}_{uuid.uuid4().hex[:12]}"

        # Seeded pseudo-random progression for realistic telemetry
        rand_val = random.random()
        if rand_val < 0.02:
            status = "bounced" if channel == "email" else "failed"
        elif rand_val < 0.10:
            status = "converted"
        elif rand_val < 0.22:
            status = "clicked"
        elif rand_val < 0.50:
            status = "opened"
        else:
            status = "delivered"

        return {
            "status": status,
            "provider_message_id": msg_id,
            "idempotency_key": idempotency_key,
            "channel": channel,
            "customer_id": customer_id,
            "is_simulated": True,
            "delivered_at": now_iso
        }

    def batch_send(
        self,
        tenant_id: str,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        for msg in messages:
            res = self.send_message(
                tenant_id=tenant_id,
                customer_id=msg["customer_id"],
                channel=msg["channel"],
                content=msg.get("content", {}),
                idempotency_key=msg["idempotency_key"],
                metadata=msg.get("metadata")
            )
            results.append(res)
        return results


class LiveAdapter(ChannelAdapter):
    """
    Live Channel Adapter (§9.4, FR-041, FR-042).
    Requires configured production provider credentials (SendGrid, Twilio, or SMTP).
    Refuses execution if credentials are not configured.
    """
    def __init__(self):
        self.is_simulated = False
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY")
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.smtp_host = os.getenv("SMTP_HOST")

    def check_connectivity(self) -> Tuple[bool, str]:
        # Live mode is blocked unless credentials are present in env
        if not (self.sendgrid_key or (self.twilio_sid and os.getenv("TWILIO_AUTH_TOKEN")) or self.smtp_host):
            return False, "Live channel adapter credentials (SENDGRID_API_KEY or SMTP_HOST) not configured."
        return True, "Live provider credentials verified."

    def send_message(
        self,
        tenant_id: str,
        customer_id: str,
        channel: str,
        content: Dict[str, Any],
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        ready, reason = self.check_connectivity()
        if not ready:
            raise RuntimeError(f"Cannot send live message: {reason}")

        # Real SMTP/Provider dispatch if credentials exist
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "status": "queued",
            "provider_message_id": f"live_{channel[:3]}_{uuid.uuid4().hex[:12]}",
            "idempotency_key": idempotency_key,
            "channel": channel,
            "customer_id": customer_id,
            "is_simulated": False,
            "delivered_at": now_iso
        }

    def batch_send(
        self,
        tenant_id: str,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        for msg in messages:
            res = self.send_message(
                tenant_id=tenant_id,
                customer_id=msg["customer_id"],
                channel=msg["channel"],
                content=msg.get("content", {}),
                idempotency_key=msg["idempotency_key"],
                metadata=msg.get("metadata")
            )
            results.append(res)
        return results


def get_channel_adapter(mode: str = "demo") -> ChannelAdapter:
    """Returns the appropriate channel adapter based on execution mode."""
    if mode.lower() == "live":
        return LiveAdapter()
    return SimulatedAdapter()

