"""
Unit Tests for Telephony Consent & Language Selection (Subtask 14)
==============================================================================
Tests:
- Consent accepted flow (Keypad 1, 2, 3) -> ai_pipeline_allowed == True, language stored
- Consent declined flow (Keypad 9) -> ai_pipeline_allowed == False, AI pipeline bypassed
- Invalid keypad input handling (Keypad 5 or letters) -> returns invalid_input status
- Repeated keypad input handling -> session updates cleanly
- TwiML prompt and response XML generation
==============================================================================
"""

import pytest
from app.agent.consent_service import (
    process_consent_digit_input,
    get_or_create_consent_session,
    generate_consent_prompt_twiml,
    generate_consent_response_twiml,
    reset_consent_registry,
)


@pytest.fixture(autouse=True)
def clean_registry():
    reset_consent_registry()
    yield
    reset_consent_registry()


def test_consent_accepted_hindi():
    """Verifies keypad 1 accepts consent for Hindi and allows AI pipeline."""
    call_sid = "CA_CONSENT_101"
    res = process_consent_digit_input(call_sid=call_sid, digits="1")

    assert res["status"] == "accepted"
    assert res["language"] == "hi"
    assert res["ai_allowed"] is True

    session = get_or_create_consent_session(call_sid)
    assert session.consent_given is True
    assert session.selected_language == "hi"
    assert session.ai_pipeline_allowed is True
    assert session.consent_timestamp is not None


def test_consent_accepted_english():
    """Verifies keypad 2 accepts consent for English."""
    call_sid = "CA_CONSENT_102"
    res = process_consent_digit_input(call_sid=call_sid, digits="2")

    assert res["status"] == "accepted"
    assert res["language"] == "en"
    assert res["ai_allowed"] is True


def test_consent_declined():
    """Verifies keypad 9 declines consent and BYPASSES AI pipeline completely."""
    call_sid = "CA_CONSENT_109"
    res = process_consent_digit_input(call_sid=call_sid, digits="9")

    assert res["status"] == "declined"
    assert res["ai_allowed"] is False

    session = get_or_create_consent_session(call_sid)
    assert session.consent_given is False
    assert session.ai_pipeline_allowed is False
    assert session.consent_timestamp is not None


def test_invalid_keypad_input():
    """Verifies that invalid digits (e.g. 5) return invalid_input and keep AI disallowed."""
    call_sid = "CA_CONSENT_105"
    res = process_consent_digit_input(call_sid=call_sid, digits="5")

    assert res["status"] == "invalid_input"
    assert res["ai_allowed"] is False

    session = get_or_create_consent_session(call_sid)
    assert session.consent_given is None
    assert session.ai_pipeline_allowed is False


def test_repeated_input_updates_session():
    """Verifies that repeated inputs update session state cleanly."""
    call_sid = "CA_REPEAT_200"

    # First invalid input
    process_consent_digit_input(call_sid=call_sid, digits="7")
    # Then valid input
    res_valid = process_consent_digit_input(call_sid=call_sid, digits="1")

    assert res_valid["status"] == "accepted"
    session = get_or_create_consent_session(call_sid)
    assert session.consent_given is True
    assert session.input_digits_history == ["7", "1"]


def test_twiml_generation():
    """Verifies TwiML generation for prompt and responses."""
    twiml_prompt = generate_consent_prompt_twiml("CA_TWIML_1")
    assert "<Response>" in twiml_prompt
    assert "<Gather" in twiml_prompt

    twiml_accepted = generate_consent_response_twiml({"status": "accepted", "language": "hi"})
    assert "<Record" in twiml_accepted

    twiml_declined = generate_consent_response_twiml({"status": "declined", "language": "hi"})
    assert "अस्वीकृत" in twiml_declined
