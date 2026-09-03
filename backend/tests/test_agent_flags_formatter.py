"""
Unit Tests for Flags Formatter & SLA Breach Predictor (Phase 9)
==============================================================================
Tests:
- Nested flags formatting (converting list of InputFlagItem to dict shape)
- Recommended action inclusion in nested flags payload
- SLA breach risk prediction calculation
==============================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.agent.flags_formatter import format_nested_flags, predict_sla_breach
from app.agent.schemas import InputFlagItem


def test_format_nested_flags():
    """Verifies that list of flags converts to nested object format."""
    flags = [
        InputFlagItem(name="trauma", confidence=0.82, signals=["long pause: 4.2s"]),
        InputFlagItem(name="intimidation", confidence=0.90, signals=["threat"])
    ]

    nested = format_nested_flags(flags, recommended_action="police_intervention, legal_aid")

    assert "trauma" in nested
    assert nested["trauma"]["present"] is True
    assert nested["trauma"]["confidence"] == 0.82
    assert nested["trauma"]["signals"] == ["long pause: 4.2s"]
    assert nested["recommended_action"] == "police_intervention, legal_aid"


def test_predict_sla_breach_fresh_case():
    """Verifies SLA prediction for fresh case (Low breach risk)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    res = predict_sla_breach(case_id=701, risk_tier="Critical", created_at_iso=now_iso)

    assert res.breach_risk_tier == "Low"
    assert res.is_breached is False
    assert res.recommended_priority_boost is False


def test_predict_sla_breach_nearing_limit():
    """Verifies SLA prediction for case nearing SLA limit (High breach risk)."""
    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=12)).isoformat()
    res = predict_sla_breach(case_id=702, risk_tier="Critical", created_at_iso=past_iso)

    assert res.breach_risk_tier in ("High", "Critical")
    assert res.recommended_priority_boost is True


def test_predict_sla_breach_exceeded_limit():
    """Verifies SLA prediction for breached case (Critical breach risk)."""
    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    res = predict_sla_breach(case_id=703, risk_tier="Critical", created_at_iso=past_iso)

    assert res.breach_risk_tier == "Critical"
    assert res.is_breached is True
    assert res.recommended_priority_boost is True
