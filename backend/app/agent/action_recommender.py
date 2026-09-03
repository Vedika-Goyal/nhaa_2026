"""
Action Recommendation Logic Module (Subtask 5)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Generates rule-based, inspectable recommended actions from SVI score, risk tier,
and perception flags.

Supported Actions:
- counselling
- legal_aid
- medical_assistance
- police_intervention
- witness_protection
- emergency_support
- standard_follow_up

Every risk assessment payload sent to POST /api/risk-assessments MUST include
the `recommended_action` string matching Vinit's backend schema (String(100)).
==============================================================================
"""

from typing import List, Dict, Any, Union, Optional
from pydantic import BaseModel, Field
from app.agent.risk_engine import _normalize_flags


CANONICAL_ACTIONS = {
    "counselling",
    "legal_aid",
    "medical_assistance",
    "police_intervention",
    "witness_protection",
    "emergency_support",
    "standard_follow_up",
}


class ActionRecommendationResult(BaseModel):
    """
    Structured action recommendation output.
    Contains both the list of actions and the formatted string for Vinit's backend.
    """
    actions: List[str] = Field(..., description="List of recommended actions")
    primary_action: str = Field(..., description="Primary / highest-priority recommended action")
    recommended_action: str = Field(..., description="String representation matching Vinit's backend Cases.recommended_action")
    rule_triggers: List[str] = Field(default_factory=list, description="Audit log of rules that triggered actions")


def recommend_actions(
    svi_score: float,
    risk_tier: str,
    flags: Union[List[Any], Dict[str, Any]]
) -> ActionRecommendationResult:
    """
    Derives inspectable recommended actions from SVI score, risk tier, and flags.

    Parameters:
        svi_score (float): SVI score [0-100]
        risk_tier (str): Calculated risk tier ('Low', 'Moderate', 'High', 'Critical')
        flags (List or Dict): Perception flag indicators

    Returns:
        ActionRecommendationResult with `recommended_action` string formatted for Vinit's backend.
    """
    score = float(svi_score)
    tier = str(risk_tier).strip().capitalize()
    normalized_flags = _normalize_flags(flags)

    actions_set = set()
    rule_triggers = []

    # 1. Base Tier Default Rules
    if tier == "Low":
        actions_set.add("standard_follow_up")
        rule_triggers.append("Base Tier Rule: Low risk tier defaults to 'standard_follow_up'.")
    elif tier == "Moderate":
        actions_set.add("counselling")
        rule_triggers.append("Base Tier Rule: Moderate risk tier includes 'counselling'.")
    elif tier == "High":
        actions_set.add("counselling")
        actions_set.add("emergency_support")
        rule_triggers.append("Base Tier Rule: High risk tier includes 'counselling' and 'emergency_support'.")
    elif tier == "Critical":
        actions_set.add("emergency_support")
        actions_set.add("police_intervention")
        rule_triggers.append("Base Tier Rule: Critical risk tier includes 'emergency_support' and 'police_intervention'.")
    else:
        actions_set.add("standard_follow_up")
        rule_triggers.append(f"Fallback Rule: Tier '{risk_tier}' defaulted to 'standard_follow_up'.")

    # 2. Flag-Based Action Rules
    for flag in normalized_flags:
        fname = flag["name"]
        fconf = flag["confidence"]

        if fconf < 0.50:
            continue

        if fname == "intimidation":
            actions_set.add("police_intervention")
            actions_set.add("legal_aid")
            rule_triggers.append(f"Flag Rule: 'intimidation' (conf {fconf:.2f}) added 'police_intervention' and 'legal_aid'.")

        elif fname == "suicidal_ideation":
            actions_set.add("counselling")
            actions_set.add("emergency_support")
            rule_triggers.append(f"Flag Rule: 'suicidal_ideation' (conf {fconf:.2f}) added 'counselling' and 'emergency_support'.")

        elif fname == "trauma":
            actions_set.add("counselling")
            actions_set.add("legal_aid")
            rule_triggers.append(f"Flag Rule: 'trauma' (conf {fconf:.2f}) added 'counselling' and 'legal_aid'.")

        elif fname in ("extreme_vulnerability", "medical"):
            actions_set.add("medical_assistance")
            actions_set.add("emergency_support")
            rule_triggers.append(f"Flag Rule: '{fname}' (conf {fconf:.2f}) added 'medical_assistance' and 'emergency_support'.")

        elif fname == "isolation":
            actions_set.add("counselling")
            rule_triggers.append(f"Flag Rule: 'isolation' (conf {fconf:.2f}) added 'counselling'.")

        elif fname == "fear" and tier in ("High", "Critical"):
            actions_set.add("witness_protection")
            rule_triggers.append(f"Flag Rule: 'fear' (conf {fconf:.2f}) at High/Critical tier added 'witness_protection'.")

    # Order priority ranking for canonical sorting
    PRIORITY_ORDER = [
        "police_intervention",
        "emergency_support",
        "medical_assistance",
        "witness_protection",
        "legal_aid",
        "counselling",
        "standard_follow_up",
    ]

    ordered_actions = [a for a in PRIORITY_ORDER if a in actions_set]
    # Add any extra actions not in priority list
    for a in actions_set:
        if a not in ordered_actions:
            ordered_actions.append(a)

    primary_action = ordered_actions[0] if ordered_actions else "standard_follow_up"
    formatted_recommended_action = ", ".join(ordered_actions)

    return ActionRecommendationResult(
        actions=ordered_actions,
        primary_action=primary_action,
        recommended_action=formatted_recommended_action,
        rule_triggers=rule_triggers
    )
