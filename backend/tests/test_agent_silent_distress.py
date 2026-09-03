"""
Unit Tests for Silent Distress Signal Abstraction (Subtask 8)
==============================================================================
Tests:
- Silent trigger causes Critical escalation (SVI 90.0, Critical tier)
- Visible transcript remains unchanged and clean (no trigger leak)
- Internal audit event generation ('silent_distress_signal_triggered')
- Confirmation is STILL required (dispatch without confirmation fails)
- Separate IVRS DTMF detection function testing
==============================================================================
"""

import pytest
from app.agent.silent_distress import (
    handle_silent_distress_signal,
    detect_dtmf_silent_signal,
    sanitize_transcript,
)
from app.agent.confirmation_gate import (
    dispatch_confirmed_action,
    reset_confirmation_registry,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Resets in-memory confirmation registry before each test."""
    reset_confirmation_registry()
    yield
    reset_confirmation_registry()


def test_dtmf_detection_function():
    """Verifies that IVRS DTMF detection correctly detects target tone sequence."""
    assert detect_dtmf_silent_signal("123555789", target_sequence="555") is True
    assert detect_dtmf_silent_signal("123456789", target_sequence="555") is False
    assert detect_dtmf_silent_signal("999", target_sequence="999") is True


def test_silent_trigger_causes_critical_escalation():
    """Verifies that silent trigger causes Critical escalation with SVI 90.0."""
    res = handle_silent_distress_signal(
        case_id=501,
        source="ivrs",
        raw_transcript="I need general information about filing a complaint.",
        metadata={"dtmf_digits": "555"}
    )

    assert res.success is True
    assert res.risk_tier == "critical"
    assert res.svi_score == 90.0
    assert res.confirmation_required is True


def test_visible_transcript_remains_unchanged():
    """Verifies that covert trigger sequence is NOT injected into the citizen transcript."""
    raw = "Hello operator 555 I need help with my application"
    clean = sanitize_transcript(raw, hidden_triggers=["555"])

    assert "555" not in clean
    assert "Hello operator  I need help with my application" in clean or "Hello operator" in clean


def test_internal_event_is_auditable():
    """Verifies that silent distress handling generates an auditable internal event payload."""
    res = handle_silent_distress_signal(
        case_id=502,
        source="chat",
        raw_transcript="Tell me about shelter home locations",
        metadata={"hidden_keyword": "silent_sos"}
    )

    audit = res.audit_event
    assert audit["event"] == "silent_distress_signal_triggered"
    assert audit["case_id"] == 502
    assert audit["source"] == "chat"
    assert audit["details"]["risk_tier"] == "critical"
    assert audit["details"]["confirmation_required"] is True


def test_confirmation_is_still_required_after_silent_signal():
    """Verifies that dispatch after silent signal STILL requires officer confirmation."""
    res = handle_silent_distress_signal(
        case_id=503,
        source="app",
        raw_transcript="Regular app feedback report",
        metadata={"gesture": "long_press_sos"}
    )

    assert res.confirmation_required is True

    # Attempting to dispatch directly without officer confirmation MUST FAIL
    with pytest.raises(ValueError) as exc:
        dispatch_confirmed_action(case_id=503, status="escalated", current_level="district")

    assert "DISPATCH BLOCKED" in str(exc.value)
