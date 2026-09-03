"""
Silent Distress Signal Abstraction Module (Subtask 8)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Provides a channel-independent handler for covert distress triggers:
- IVRS: Configurable DTMF keypad sequence
- Chatbot: Hidden trigger keywords
- Mobile App: Long-press SOS gesture

Behaviors & Invariants:
1. Elevates risk assessment to Critical tier (SVI >= 75)
2. Triggers the Critical human-confirmation safety flow (prepare_critical_action)
3. Preserves normal visible/audible conversation (transcript remains clean)
4. Excludes covert trigger sequence/keywords from public citizen transcript
5. Generates an auditable internal event log
6. NEVER autonomously dispatches emergency services (requires officer confirmation gate).
==============================================================================
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from app.agent.confirmation_gate import prepare_critical_action, CriticalActionRecord


# Configurable Default DTMF Sequence for IVRS
DEFAULT_DTMF_SEQUENCE = os.environ.get("SILENT_DISTRESS_DTMF", "555")

# Supported Channel Sources
VALID_SILENT_SOURCES = {"ivrs", "chat", "chatbot", "app", "mobile_app", "portal"}


class SilentDistressResult(BaseModel):
    """
    Structured outcome of handle_silent_distress_signal execution.
    """
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    case_id: int
    source: str
    risk_tier: str = Field(default="critical")
    svi_score: float = Field(default=90.0)
    visible_transcript_clean: bool = Field(default=True)
    confirmation_required: bool = Field(default=True)
    action_record_id: str
    audit_event: Dict[str, Any]


def detect_dtmf_silent_signal(dtmf_digits: str, target_sequence: Optional[str] = None) -> bool:
    """
    Separate IVRS DTMF detection logic.
    Returns True if target DTMF sequence is present in digits.
    """
    target = target_sequence or DEFAULT_DTMF_SEQUENCE
    clean_digits = str(dtmf_digits).strip()
    return target in clean_digits


def sanitize_transcript(transcript: Optional[str], hidden_triggers: Optional[List[str]] = None) -> str:
    """
    Ensures hidden trigger sequences/keywords are stripped from the visible citizen transcript.
    """
    if not transcript:
        return ""

    sanitized = transcript
    triggers_to_strip = hidden_triggers or [DEFAULT_DTMF_SEQUENCE, "silent_sos", "covert_trigger"]
    for trig in triggers_to_strip:
        sanitized = sanitized.replace(trig, "").strip()

    return sanitized


def handle_silent_distress_signal(
    case_id: int,
    source: str,
    raw_transcript: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> SilentDistressResult:
    """
    Channel-independent handler for Silent Distress Signals.

    1. Marks case for Critical escalation (SVI 90.0, RiskTier Critical)
    2. Enters Critical human-confirmation flow via prepare_critical_action()
    3. Preserves clean visible transcript without injecting trigger sequence
    4. Emits an internally auditable event payload
    5. Leaves action in pending_confirmation state (no autonomous dispatch)
    """
    clean_source = str(source).strip().lower()
    if clean_source not in VALID_SILENT_SOURCES:
        clean_source = "ivrs"

    meta = metadata or {}

    # 1. Clean public transcript
    clean_transcript = sanitize_transcript(raw_transcript, meta.get("hidden_triggers"))

    # 2. Trigger Critical human-confirmation flow
    action_record = prepare_critical_action(
        case_id=case_id,
        action="police_intervention",
        risk_tier="critical",
        svi_score=90.0
    )

    # 3. Create Auditable Internal Event
    audit_event = {
        "event": "silent_distress_signal_triggered",
        "case_id": case_id,
        "source": clean_source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {
            "svi_score": 90.0,
            "risk_tier": "critical",
            "confirmation_required": True,
            "visible_transcript": clean_transcript,
            "raw_metadata": {k: v for k, v in meta.items() if k != "sensitive_raw_dtmf"}
        }
    }

    return SilentDistressResult(
        success=True,
        case_id=case_id,
        source=clean_source,
        risk_tier="critical",
        svi_score=90.0,
        visible_transcript_clean=True,
        confirmation_required=True,
        action_record_id=action_record.record_id,
        audit_event=audit_event
    )
