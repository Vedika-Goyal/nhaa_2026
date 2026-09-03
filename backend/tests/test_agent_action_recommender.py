"""
Unit Tests for Action Recommendation Logic (Subtask 5)
==============================================================================
Tests:
- Low risk tier recommendations
- Moderate risk tier recommendations
- High risk tier recommendations
- Critical risk tier recommendations
- Multiple action aggregations (High + intimidation -> police + legal aid)
- Critical + medical vulnerability -> medical + emergency support
- Conflicting indicators handling
- Empty flags handling
- String format matching Vinit's backend Cases.recommended_action
==============================================================================
"""

import pytest
from app.agent.action_recommender import recommend_actions
from app.agent.schemas import InputFlagItem


def test_low_risk_empty_flags():
    """Tests Low risk tier with empty flags defaults to standard_follow_up."""
    res = recommend_actions(svi_score=10.0, risk_tier="Low", flags=[])
    assert "standard_follow_up" in res.actions
    assert res.recommended_action == "standard_follow_up"


def test_moderate_risk_tier():
    """Tests Moderate risk tier defaults to counselling."""
    res = recommend_actions(svi_score=35.0, risk_tier="Moderate", flags=[])
    assert "counselling" in res.actions
    assert res.recommended_action == "counselling"


def test_high_risk_tier():
    """Tests High risk tier defaults to counselling and emergency_support."""
    res = recommend_actions(svi_score=60.0, risk_tier="High", flags=[])
    assert "emergency_support" in res.actions
    assert "counselling" in res.actions


def test_critical_risk_tier():
    """Tests Critical risk tier defaults to emergency_support and police_intervention."""
    res = recommend_actions(svi_score=85.0, risk_tier="Critical", flags=[])
    assert "police_intervention" in res.actions
    assert "emergency_support" in res.actions


def test_high_risk_plus_intimidation_multiple_actions():
    """Tests High tier + intimidation -> police_intervention + legal_aid + emergency_support + counselling."""
    flags = [
        InputFlagItem(name="intimidation", confidence=0.85, signals=["Keyword match: 'threat'"])
    ]
    res = recommend_actions(svi_score=65.0, risk_tier="High", flags=flags)

    assert "police_intervention" in res.actions
    assert "legal_aid" in res.actions
    assert "emergency_support" in res.actions
    assert "counselling" in res.actions
    assert isinstance(res.recommended_action, str)
    assert "police_intervention" in res.recommended_action


def test_critical_plus_medical_vulnerability():
    """Tests Critical tier + medical vulnerability -> medical_assistance + emergency_support + police_intervention."""
    flags = [
        {"name": "extreme_vulnerability", "confidence": 0.80, "signals": ["injury"]}
    ]
    res = recommend_actions(svi_score=90.0, risk_tier="Critical", flags=flags)

    assert "medical_assistance" in res.actions
    assert "emergency_support" in res.actions
    assert "police_intervention" in res.actions


def test_conflicting_indicators_handling():
    """Tests handling of conflicting indicators (e.g. low score with high threat flags)."""
    flags = [
        {"name": "intimidation", "confidence": 0.90, "signals": ["threat"]},
        {"name": "trauma", "confidence": 0.75, "signals": ["flashback"]}
    ]
    res = recommend_actions(svi_score=15.0, risk_tier="Low", flags=flags)

    assert "police_intervention" in res.actions
    assert "legal_aid" in res.actions
    assert "counselling" in res.actions
    assert len(res.actions) >= 3
