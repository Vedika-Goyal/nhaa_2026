"""
Unit Tests for Rule-Based Risk Tier Engine (Subtask 3)
==============================================================================
Tests:
- Numeric SVI score boundary thresholds (0, 24, 25, 49, 50, 74, 75, 100)
- Explicit flag override rules (suicidal_ideation -> Critical, intimidation -> High)
- Multiple vulnerability flags elevation rule
- Explainability breakdown structure
==============================================================================
"""

import pytest
from app.agent.risk_engine import (
    score_flags_to_tier,
    get_base_tier_from_svi,
    LOW_TIER_MAX_SCORE,
    MODERATE_TIER_MAX_SCORE,
    HIGH_TIER_MAX_SCORE,
    CRITICAL_TIER_MIN_SCORE,
)
from app.agent.schemas import InputFlagItem


def test_base_svi_tier_boundaries():
    """Tests exact SVI score boundary thresholds."""
    assert get_base_tier_from_svi(0.0) == "Low"
    assert get_base_tier_from_svi(24.0) == "Low"
    assert get_base_tier_from_svi(24.5) == "Moderate"
    assert get_base_tier_from_svi(25.0) == "Moderate"
    assert get_base_tier_from_svi(49.0) == "Moderate"
    assert get_base_tier_from_svi(49.5) == "High"
    assert get_base_tier_from_svi(50.0) == "High"
    assert get_base_tier_from_svi(74.0) == "High"
    assert get_base_tier_from_svi(74.5) == "Critical"
    assert get_base_tier_from_svi(75.0) == "Critical"
    assert get_base_tier_from_svi(100.0) == "Critical"


def test_svi_tier_without_flags():
    """Tests score_flags_to_tier with empty flags list."""
    decision_low = score_flags_to_tier(15.0, [])
    assert decision_low.risk_tier == "Low"
    assert decision_low.override_applied is False

    decision_high = score_flags_to_tier(60.0, [])
    assert decision_high.risk_tier == "High"
    assert decision_high.override_applied is False


def test_suicidal_ideation_override_to_critical():
    """Tests that high-confidence suicidal_ideation elevates a Low SVI score (15.0) to Critical."""
    flags = [
        InputFlagItem(name="suicidal_ideation", confidence=0.85, signals=["Keyword match: 'जीना नहीं'"])
    ]
    decision = score_flags_to_tier(15.0, flags)

    assert decision.base_svi_tier == "Low"
    assert decision.final_risk_tier == "Critical"
    assert decision.risk_tier == "Critical"
    assert decision.override_applied is True
    assert "suicidal_ideation" in decision.override_reason


def test_intimidation_override_to_high():
    """Tests that high-confidence intimidation elevates a Low SVI score (20.0) to High."""
    flags = [
        InputFlagItem(name="intimidation", confidence=0.75, signals=["Keyword match: 'धमकी'"])
    ]
    decision = score_flags_to_tier(20.0, flags)

    assert decision.base_svi_tier == "Low"
    assert decision.final_risk_tier == "High"
    assert decision.risk_tier == "High"
    assert decision.override_applied is True
    assert "intimidation" in decision.override_reason


def test_multiple_vulnerability_flags_override():
    """Tests that multiple vulnerable flags elevate Low SVI score to Moderate."""
    flags = [
        {"name": "isolation", "confidence": 0.68, "signals": ["social isolation"]},
        {"name": "depression", "confidence": 0.70, "signals": ["hopelessness"]}
    ]
    decision = score_flags_to_tier(10.0, flags)

    assert decision.base_svi_tier == "Low"
    assert decision.final_risk_tier == "Moderate"
    assert decision.override_applied is True


def test_explainability_payload_structure():
    """Verifies that the decision decision contains a complete explainability payload."""
    flags = [
        {"name": "intimidation", "confidence": 0.80, "signals": ["threat"]}
    ]
    decision = score_flags_to_tier(30.0, flags)

    exp = decision.explanation
    assert "svi_contribution" in exp
    assert exp["svi_contribution"]["score"] == 30.0
    assert exp["svi_contribution"]["base_tier"] == "Moderate"
    assert "flag_contribution" in exp
    assert exp["flag_contribution"]["total_flags"] == 1
    assert "override_rule" in exp
    assert exp["override_rule"]["applied"] is True
