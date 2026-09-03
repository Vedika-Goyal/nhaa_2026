"""
AI-Officer Consistency Check Module (Subtask 9 / Phase 8)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Compares the AI-predicted risk tier against an officer's manual classification.
If the tiers differ by more than 1 level in the tier hierarchy:
    Low (0) <-> Moderate (1) <-> High (2) <-> Critical (3)
Flags an append-only audit event ('ai_officer_tier_mismatch') for supervisor review.
==============================================================================
"""

from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import BaseModel, Field, ConfigDict

TIER_RANKS: Dict[str, int] = {
    "low": 0,
    "moderate": 1,
    "high": 2,
    "critical": 3,
}


class ConsistencyCheckResult(BaseModel):
    """
    Structured outcome of the AI vs Officer consistency evaluation.
    """
    model_config = ConfigDict(protected_namespaces=())

    case_id: int
    ai_tier: str
    officer_tier: str
    tier_difference: int
    is_mismatch: bool = Field(..., description="True if tier difference > 1 level")
    requires_supervisor_review: bool = Field(..., description="True if flagged for supervisor review")
    audit_event: Dict[str, Any] = Field(..., description="Auditable event payload")


def check_ai_officer_consistency(ai_tier: str, officer_tier: str, case_id: int) -> ConsistencyCheckResult:
    """
    Compares AI-predicted tier against officer manual tier.

    Returns ConsistencyCheckResult flagging mismatches where abs(rank_diff) > 1.
    """
    ai_clean = str(ai_tier).strip().lower()
    officer_clean = str(officer_tier).strip().lower()

    if ai_clean not in TIER_RANKS:
        ai_clean = "moderate"
    if officer_clean not in TIER_RANKS:
        officer_clean = "moderate"

    ai_rank = TIER_RANKS[ai_clean]
    officer_rank = TIER_RANKS[officer_clean]

    tier_diff = abs(ai_rank - officer_rank)
    is_mismatch = tier_diff > 1

    audit_event = {
        "event": "ai_officer_tier_mismatch" if is_mismatch else "ai_officer_tier_consistency_verified",
        "case_id": case_id,
        "ai_tier": ai_clean.capitalize(),
        "officer_tier": officer_clean.capitalize(),
        "tier_difference": tier_diff,
        "requires_supervisor_review": is_mismatch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {
            "ai_rank": ai_rank,
            "officer_rank": officer_rank,
            "mismatch_threshold": 1
        }
    }

    return ConsistencyCheckResult(
        case_id=case_id,
        ai_tier=ai_clean.capitalize(),
        officer_tier=officer_clean.capitalize(),
        tier_difference=tier_diff,
        is_mismatch=is_mismatch,
        requires_supervisor_review=is_mismatch,
        audit_event=audit_event
    )
