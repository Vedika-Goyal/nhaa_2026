"""
Flags Format & SLA Risk Predictor Module (Phase 9 / Subtask 10)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
1. Converts flat/listed perception flags into the official nested-object format:
   {
     "trauma": {
       "present": true,
       "confidence": 0.82,
       "signals": ["long pause: 4.2s"]
     },
     "recommended_action": "police_intervention, legal_aid"
   }

2. Simple SLA Breach Risk Predictor for Pawan's Admin Panel SLACountdown styling.
==============================================================================
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Union, Optional
from pydantic import BaseModel, Field
from app.agent.risk_engine import _normalize_flags


def format_nested_flags(
    flags: Union[List[Any], Dict[str, Any]],
    recommended_action: Optional[str] = None
) -> Dict[str, Any]:
    """
    Converts list of flags into the official nested object shape for DB storage & frontend rendering.
    """
    normalized = _normalize_flags(flags)
    nested_output: Dict[str, Any] = {}

    for f in normalized:
        fname = f["name"]
        fconf = f["confidence"]
        fsignals = f.get("signals", [])

        nested_output[fname] = {
            "present": fconf >= 0.50,
            "confidence": round(fconf, 2),
            "signals": fsignals
        }

    if recommended_action:
        nested_output["recommended_action"] = str(recommended_action).strip()

    return nested_output


class SLAPredictionResult(BaseModel):
    """
    Outcome of SLA breach risk predictor.
    """
    case_id: int
    risk_tier: str
    elapsed_minutes: float
    sla_limit_minutes: float
    breach_risk_tier: str  # 'Low', 'Moderate', 'High', 'Critical'
    is_breached: bool
    recommended_priority_boost: bool


def predict_sla_breach(
    case_id: int,
    risk_tier: str,
    created_at_iso: str
) -> SLAPredictionResult:
    """
    Predicts SLA breach risk based on case age and risk tier.
    """
    tier_clean = str(risk_tier).strip().lower()

    # SLA limits by tier (in minutes)
    SLA_LIMITS = {
        "critical": 15.0,    # 15 mins for Critical
        "high": 60.0,        # 1 hour for High
        "moderate": 240.0,   # 4 hours for Moderate
        "low": 1440.0       # 24 hours for Low
    }

    limit_mins = SLA_LIMITS.get(tier_clean, 60.0)

    try:
        created_dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        elapsed_mins = max(0.0, (now_dt - created_dt).total_seconds() / 60.0)
    except Exception:
        elapsed_mins = 0.0

    ratio = elapsed_mins / limit_mins if limit_mins > 0 else 0.0
    is_breached = elapsed_mins >= limit_mins

    if ratio >= 1.0 or is_breached:
        breach_risk = "Critical"
    elif ratio >= 0.75:
        breach_risk = "High"
    elif ratio >= 0.50:
        breach_risk = "Moderate"
    else:
        breach_risk = "Low"

    return SLAPredictionResult(
        case_id=case_id,
        risk_tier=tier_clean.capitalize(),
        elapsed_minutes=round(elapsed_mins, 1),
        sla_limit_minutes=limit_mins,
        breach_risk_tier=breach_risk,
        is_breached=is_breached,
        recommended_priority_boost=ratio >= 0.75
    )
