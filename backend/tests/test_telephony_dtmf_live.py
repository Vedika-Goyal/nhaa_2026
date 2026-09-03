"""
Unit Tests for Live Twilio DTMF Detection & Escalation (Subtask 16)
==============================================================================
Tests:
- Configured DTMF sequence ('555') triggers Critical escalation
- Non-matching DTMF sequence ('123') does not trigger Critical escalation
- Visible transcript remains clean and unchanged
- Case becomes Critical and enters pending_confirmation flow
- Human officer confirmation is STILL required (unconfirmed dispatch fails)
- POST /api/v1/telephony/dtmf endpoint does not announce escalation in TwiML
==============================================================================
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agent.telephony_service import process_telephony_dtmf
from app.agent.confirmation_gate import dispatch_confirmed_action, reset_confirmation_registry
from app.agent.silent_distress import sanitize_transcript

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_registry():
    reset_confirmation_registry()
    yield
    reset_confirmation_registry()


def test_correct_sequence_triggers_critical_escalation():
    """Verifies that pressing configured DTMF sequence ('555') triggers Critical escalation."""
    res = process_telephony_dtmf(call_sid="CA_LIVE_DTMF_555", dtmf_digits="555", case_id=901)

    assert res["silent_signal_detected"] is True
    assert res["case_id"] == 901

    payload = res["result"]
    assert payload["risk_tier"] == "critical"
    assert payload["svi_score"] == 90.0
    assert payload["confirmation_required"] is True


def test_incorrect_sequence_does_not_trigger():
    """Verifies that non-matching DTMF digits ('123') do NOT trigger Critical escalation."""
    res = process_telephony_dtmf(call_sid="CA_LIVE_DTMF_123", dtmf_digits="123", case_id=902)

    assert res["silent_signal_detected"] is False
    assert "result" not in res


def test_visible_transcript_remains_unchanged():
    """Verifies that covert DTMF trigger sequence is not injected into the public transcript."""
    raw_transcript = "Caller spoke normal query 555 for information"
    clean = sanitize_transcript(raw_transcript, hidden_triggers=["555"])

    assert "555" not in clean
    assert "Caller spoke normal query" in clean


def test_confirmation_still_required_after_live_dtmf():
    """Verifies that Critical escalation via live DTMF STILL requires officer confirmation."""
    res = process_telephony_dtmf(call_sid="CA_LIVE_DTMF_CONFIRM", dtmf_digits="555", case_id=903)

    assert res["silent_signal_detected"] is True

    # Unconfirmed dispatch MUST FAIL
    with pytest.raises(ValueError) as exc:
        dispatch_confirmed_action(case_id=903, status="escalated", current_level="district")

    assert "DISPATCH BLOCKED" in str(exc.value)


def test_dtmf_endpoint_response_does_not_announce_escalation():
    """Verifies POST /api/v1/telephony/dtmf returns normal TwiML without exposing escalation."""
    response = client.post(
        "/api/v1/telephony/dtmf",
        data={"CallSid": "CA_LIVE_ENDPOINT", "Digits": "555"}
    )

    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")

    body_xml = response.text
    assert "<Response>" in body_xml
    # Must NOT mention Critical or Emergency escalation in public audio
    assert "Critical" not in body_xml
    assert "Emergency" not in body_xml
    assert "Escalated" not in body_xml
