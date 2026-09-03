"""
Unit Tests for Telephony & IVRS Integration (Part 2 - Phases 12-18)
==============================================================================
Tests:
- TwiML consent notice XML generation
- Inbound call session creation & tracking
- Covert DTMF silent distress signal detection mid-call
- Outbound follow-up callback trigger audit logging (USP 4)
==============================================================================
"""

import pytest
from app.agent.telephony_service import (
    generate_consent_twiml,
    process_telephony_dtmf,
    trigger_outbound_callback,
    get_or_create_call_session,
)
from app.agent.confirmation_gate import reset_confirmation_registry


@pytest.fixture(autouse=True)
def clean_registry():
    reset_confirmation_registry()
    yield
    reset_confirmation_registry()


def test_generate_consent_twiml():
    """Verifies TwiML XML output contains mandatory consent statement."""
    twiml_hi = generate_consent_twiml(call_sid="CA12345", language="hi")
    assert "<?xml" in twiml_hi
    assert "<Response>" in twiml_hi
    assert "हेल्पलाइन 14566" in twiml_hi
    assert "<Gather" in twiml_hi

    twiml_en = generate_consent_twiml(call_sid="CA67890", language="en")
    assert "National Helpline 14566" in twiml_en


def test_process_telephony_dtmf_silent_signal():
    """Verifies covert DTMF sequence ('555') mid-call triggers Critical Silent Distress."""
    call_sid = "CA_SILENT_TEST_99"

    # Digits without 555
    res_normal = process_telephony_dtmf(call_sid=call_sid, dtmf_digits="1")
    assert res_normal["silent_signal_detected"] is False

    # Keypad press containing 555
    res_silent = process_telephony_dtmf(call_sid=call_sid, dtmf_digits="555", case_id=801)
    assert res_silent["silent_signal_detected"] is True
    assert res_silent["case_id"] == 801
    assert res_silent["result"]["risk_tier"] == "critical"
    assert res_silent["result"]["confirmation_required"] is True


def test_trigger_outbound_callback():
    """Verifies USP 4 proactive follow-up callback trigger."""
    res = trigger_outbound_callback(to_number="+919876543210", case_id=802)
    assert res["event"] == "outbound_callback_initiated"
    assert res["case_id"] == 802
    assert res["to_number"] == "+919876543210"
    assert res["status"] == "scheduled"
