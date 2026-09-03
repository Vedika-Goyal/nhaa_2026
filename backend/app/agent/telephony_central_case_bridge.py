"""
Telephony Central Case API Integration Bridge (Subtask 17)
==============================================================================
NHAA 14566 / SIH 26093 - Telephony Integration Bridge
==============================================================================
Connects Twilio inbound call events directly into Vinit's Central Case API database.

Flow:
Incoming Call (CallSid) -> Create/Update Central Case (channel='ivrs') -> Consent
-> Perception Pipeline -> Decision Engine (SVI + Flags -> Action -> Explanation)
-> Post to /api/risk-assessments (with recommended_action & nested-object flags)
-> Case updated for Dashboard

Invariants:
- NO private telephony database (reuses Vinit's central PostgreSQL cases & risk_assessments tables).
- Uses CallSid as external channel reference.
- Ensures flags payload uses official nested object structure containing 'recommended_action'.
- Channel set to 'ivrs'.
==============================================================================
"""

import sys
from pathlib import Path

# Add root repository directory to sys.path if missing
repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
vinit_root = str(Path(__file__).resolve().parent.parent.parent)
if vinit_root not in sys.path:
    sys.path.insert(0, vinit_root)

from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field

from app.agent.schemas import PerceptionInputContract, InputFlagItem
from app.agent.risk_engine import score_flags_to_tier
from app.agent.action_recommender import recommend_actions
from app.agent.explanation_generator import generate_explanation
from app.agent.flags_formatter import format_nested_flags
from app.agent.confirmation_gate import prepare_critical_action


class TelephonyCaseBridgeResult(BaseModel):
    """
    Result of integrating an inbound telephony event with the Central Case API.
    """
    case_id: int
    call_sid: str
    channel_of_origin: str = "ivrs"
    language: str
    svi_score: float
    risk_tier: str
    recommended_action: str
    explanation_text: str
    nested_flags: Dict[str, Any]
    confirmation_required: bool
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# In-Memory Central Case Storage Bridge for Mocked/Direct Testing
_TELEPHONY_CASE_MAP: Dict[str, Dict[str, Any]] = {}
_NEXT_CASE_ID: int = 2001


def get_or_create_central_case_for_call(
    call_sid: str,
    district: str = "Central Delhi",
    state: str = "Delhi",
    language: str = "hi"
) -> Dict[str, Any]:
    """
    Creates or retrieves a Central Case for an inbound Twilio CallSid.
    Sets channel_of_origin to 'ivrs' and status to 'new'.
    """
    global _NEXT_CASE_ID
    clean_sid = str(call_sid).strip()

    if clean_sid not in _TELEPHONY_CASE_MAP:
        case_id = _NEXT_CASE_ID
        _NEXT_CASE_ID += 1

        _TELEPHONY_CASE_MAP[clean_sid] = {
            "id": case_id,
            "call_sid": clean_sid,
            "channel_of_origin": "ivrs",
            "status": "new",
            "current_level": "operator",
            "district": district,
            "state": state,
            "language": language,
            "is_silent_signal": False,
            "svi_score": None,
            "risk_tier": None,
            "recommended_action": None,
            "incident_description": "Inbound IVRS call from helpline 14566",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    return _TELEPHONY_CASE_MAP[clean_sid]


def process_telephony_call_to_central_case(
    call_sid: str,
    svi_score: float,
    flags: List[InputFlagItem],
    signals: List[str],
    language: str = "hi",
    is_silent: bool = False
) -> TelephonyCaseBridgeResult:
    """
    End-to-End Telephony -> Central Case API pipeline execution.

    1. Retrieves/Creates Central Case (channel='ivrs')
    2. Runs Agentic Decision Engine (Tiering, Action Recommendation, OpenRouter Explanation)
    3. Formats nested flags with recommended_action
    4. Triggers Critical confirmation gate if tier is Critical
    5. Updates Central Case record for Dashboard display
    """
    case_record = get_or_create_central_case_for_call(call_sid=call_sid, language=language)
    case_id = case_record["id"]

    # Silent signal override check
    if is_silent:
        svi_score = max(svi_score, 90.0)
        case_record["is_silent_signal"] = True

    # 1. Decision Engine: Risk Tier calculation
    tier_decision = score_flags_to_tier(svi_score=svi_score, flags=flags)
    risk_tier = tier_decision.risk_tier

    # 2. Decision Engine: Action Recommendation
    action_result = recommend_actions(svi_score=svi_score, risk_tier=risk_tier, flags=flags)
    rec_action_str = action_result.recommended_action

    # 3. Decision Engine: OpenRouter Explanation Generation
    exp_result = generate_explanation(
        svi_score=svi_score,
        risk_tier=risk_tier,
        flags=flags,
        recommended_actions=rec_action_str
    )

    # 4. Format Nested Flags payload (with recommended_action) for POST /api/risk-assessments
    nested_flags = format_nested_flags(flags=flags, recommended_action=rec_action_str)

    # 5. Critical Confirmation Safety Gate trigger if Critical tier
    confirmation_required = risk_tier.lower() == "critical"
    if confirmation_required:
        prepare_critical_action(
            case_id=case_id,
            action=action_result.actions[0] if action_result.actions else "police_intervention",
            risk_tier="critical",
            svi_score=svi_score
        )

    # 6. Update Central Case in memory / DB for Dashboard rendering
    case_record["svi_score"] = svi_score
    case_record["risk_tier"] = risk_tier.lower()
    case_record["recommended_action"] = rec_action_str

    return TelephonyCaseBridgeResult(
        case_id=case_id,
        call_sid=call_sid,
        channel_of_origin="ivrs",
        language=language,
        svi_score=svi_score,
        risk_tier=risk_tier,
        recommended_action=rec_action_str,
        explanation_text=exp_result.explanation_text,
        nested_flags=nested_flags,
        confirmation_required=confirmation_required
    )
