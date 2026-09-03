"""
Rule-Based Risk Tier Engine (Subtask 3)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Computes the final risk tier (Low, Moderate, High, Critical) from SVI score
and perception flags using named configurable thresholds and explicit overrides.

Design Principles:
- Configurable named constants (No hardcoded inline magic numbers)
- Transparent, explainable decision trail for auditability
- Explicit override rules (e.g. suicidal_ideation -> Critical, intimidation -> High)
- Non-clinical: Treat flags strictly as perception risk indicators.
==============================================================================
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field


# ── Configurable Named Thresholds ──────────────────────────────────────────
LOW_TIER_MAX_SCORE: float = 24.0
MODERATE_TIER_MAX_SCORE: float = 49.0
HIGH_TIER_MAX_SCORE: float = 74.0
CRITICAL_TIER_MIN_SCORE: float = 75.0

# ── Flag Override Confidence Thresholds ────────────────────────────────────
HIGH_CONFIDENCE_THRESHOLD: float = 0.70
VULNERABILITY_CONFIDENCE_THRESHOLD: float = 0.65

# ── Explicit Flag Override Rules ───────────────────────────────────────────
# Flags that force minimum Critical risk tier when confidence >= 0.70
CRITICAL_MINIMUM_FLAGS: set = {"suicidal_ideation"}

# Flags that force minimum High risk tier when confidence >= 0.70
HIGH_MINIMUM_FLAGS: set = {"intimidation", "trauma"}

# Tier order for hierarchy comparison
TIER_HIERARCHY: Dict[str, int] = {
    "Low": 0,
    "Moderate": 1,
    "High": 2,
    "Critical": 3,
}

TIER_BY_INDEX: Dict[int, str] = {
    0: "Low",
    1: "Moderate",
    2: "High",
    3: "Critical",
}


class RiskTierDecision(BaseModel):
    """
    Structured outcome of the rule-based risk tier decision.
    Contains full explainability metrics for auditability.
    """
    risk_tier: str = Field(..., description="Final risk tier: 'Low', 'Moderate', 'High', 'Critical'")
    base_svi_tier: str = Field(..., description="Risk tier derived purely from numeric SVI score")
    final_risk_tier: str = Field(..., description="Final risk tier after applying explicit overrides")
    svi_score: float = Field(..., ge=0.0, le=100.0, description="Raw SVI score [0-100]")
    override_applied: bool = Field(default=False, description="True if a flag override elevated the risk tier")
    override_reason: Optional[str] = Field(default=None, description="Human-readable explanation of applied override rule")
    explanation: Dict[str, Any] = Field(..., description="Detailed breakdown of SVI, flags, and rules applied")


def get_base_tier_from_svi(svi_score: float) -> str:
    """
    Lookup base risk tier from named SVI threshold constants.
    """
    score = float(svi_score)
    if score <= LOW_TIER_MAX_SCORE:
        return "Low"
    elif score <= MODERATE_TIER_MAX_SCORE:
        return "Moderate"
    elif score <= HIGH_TIER_MAX_SCORE:
        return "High"
    else:
        return "Critical"


def _normalize_flags(flags: Union[List[Any], Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalizes input flags into a standard list of flag dictionaries:
    [{ "name": str, "confidence": float, "signals": List[str] }]
    """
    normalized = []
    if isinstance(flags, list):
        for item in flags:
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            elif isinstance(item, dict):
                item_dict = item
            else:
                continue

            fname = str(item_dict.get("name", "")).strip().lower()
            fconf = float(item_dict.get("confidence", 0.50))
            fsignals = item_dict.get("signals", [])
            if fname:
                normalized.append({
                    "name": fname,
                    "confidence": fconf,
                    "signals": fsignals,
                })

    elif isinstance(flags, dict):
        for fname, val in flags.items():
            clean_name = fname.strip().lower()
            if isinstance(val, dict):
                fconf = float(val.get("confidence", 0.50 if val.get("present") else 0.0))
                fsignals = val.get("signals", [])
            elif isinstance(val, bool):
                fconf = 1.0 if val else 0.0
                fsignals = []
            elif isinstance(val, (int, float)):
                fconf = float(val)
                fsignals = []
            else:
                continue

            if clean_name and fconf > 0.0:
                normalized.append({
                    "name": clean_name,
                    "confidence": fconf,
                    "signals": fsignals,
                })

    return normalized


def score_flags_to_tier(
    svi_score: float,
    flags: Union[List[Any], Dict[str, Any]]
) -> RiskTierDecision:
    """
    Computes final Risk Tier (Low, Moderate, High, Critical) from SVI score and flags.
    
    Logic:
    1. Determine base_svi_tier using named numeric bounds (LOW_TIER_MAX_SCORE, etc.)
    2. Check explicit flag override rules:
       - suicidal_ideation (conf >= 0.70) -> Forces minimum Critical tier
       - intimidation or trauma (conf >= 0.70) -> Forces minimum High tier
       - >= 2 high-confidence vulnerability indicators (conf >= 0.65) -> Forces minimum Moderate tier
    3. Final tier = max(base_svi_tier, override_min_tier)
    4. Package decision with complete explainability breakdown.
    """
    score = float(svi_score)
    base_tier = get_base_tier_from_svi(score)
    normalized_flags = _normalize_flags(flags)

    override_tier_level = TIER_HIERARCHY[base_tier]
    override_applied = False
    override_reasons = []

    # Check 1: Suicidal Ideation Override (Forces Critical)
    for flag in normalized_flags:
        if flag["name"] in CRITICAL_MINIMUM_FLAGS and flag["confidence"] >= HIGH_CONFIDENCE_THRESHOLD:
            target_level = TIER_HIERARCHY["Critical"]
            if target_level > override_tier_level:
                override_tier_level = target_level
                override_applied = True
                override_reasons.append(
                    f"Explicit Safety Rule: Severe flag '{flag['name']}' (confidence {flag['confidence']:.2f}) forces minimum Critical tier."
                )

    # Check 2: Intimidation / Severe Trauma Override (Forces High)
    for flag in normalized_flags:
        if flag["name"] in HIGH_MINIMUM_FLAGS and flag["confidence"] >= HIGH_CONFIDENCE_THRESHOLD:
            target_level = TIER_HIERARCHY["High"]
            if target_level > override_tier_level:
                override_tier_level = target_level
                override_applied = True
                override_reasons.append(
                    f"Explicit Safety Rule: High threat flag '{flag['name']}' (confidence {flag['confidence']:.2f}) forces minimum High tier."
                )

    # Check 3: Multiple High-Confidence Vulnerability Flags (Forces Moderate minimum)
    vulnerable_flags = [f for f in normalized_flags if f["confidence"] >= VULNERABILITY_CONFIDENCE_THRESHOLD]
    if len(vulnerable_flags) >= 2 and override_tier_level < TIER_HIERARCHY["Moderate"]:
        override_tier_level = TIER_HIERARCHY["Moderate"]
        override_applied = True
        flag_names = ", ".join([f["name"] for f in vulnerable_flags])
        override_reasons.append(
            f"Multi-Signal Rule: Multiple vulnerable indicators ({flag_names}) forces minimum Moderate tier."
        )

    final_tier = TIER_BY_INDEX[override_tier_level]
    override_reason_text = " | ".join(override_reasons) if override_reasons else None

    # Construct explainability detail
    explanation = {
        "svi_contribution": {
            "score": score,
            "base_tier": base_tier,
            "thresholds": {
                "low_max": LOW_TIER_MAX_SCORE,
                "moderate_max": MODERATE_TIER_MAX_SCORE,
                "high_max": HIGH_TIER_MAX_SCORE,
                "critical_min": CRITICAL_TIER_MIN_SCORE,
            }
        },
        "flag_contribution": {
            "total_flags": len(normalized_flags),
            "flag_summary": [
                {
                    "name": f["name"],
                    "confidence": f["confidence"],
                    "signals_count": len(f["signals"])
                } for f in normalized_flags
            ]
        },
        "override_rule": {
            "applied": override_applied,
            "reason": override_reason_text,
            "elevated_from": base_tier if override_applied else None,
            "elevated_to": final_tier if override_applied else None,
        }
    }

    return RiskTierDecision(
        risk_tier=final_tier,
        base_svi_tier=base_tier,
        final_risk_tier=final_tier,
        svi_score=score,
        override_applied=override_applied,
        override_reason=override_reason_text,
        explanation=explanation
    )
