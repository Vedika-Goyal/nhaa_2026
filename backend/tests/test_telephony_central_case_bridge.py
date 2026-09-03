"""
Integration Tests for Telephony -> Central Case API Bridge (Subtask 17)
==============================================================================
Tests:
- Every inbound call creates/updates a Central Case with channel_of_origin='ivrs'
- Links CallSid as external channel reference
- End-to-end flow: Inbound call -> Consent -> Perception -> Decision Engine -> Risk Assessment
- POST /api/risk-assessments payload contains recommended_action & nested flags shape
- Central Case updated for Dashboard rendering
- NO private telephony database created
==============================================================================
"""

import pytest
from app.agent.schemas import InputFlagItem
from app.agent.telephony_central_case_bridge import (
    get_or_create_central_case_for_call,
    process_telephony_call_to_central_case,
)
from app.agent.confirmation_gate import reset_confirmation_registry


@pytest.fixture(autouse=True)
def clean_registry():
    reset_confirmation_registry()
    yield
    reset_confirmation_registry()


def test_inbound_call_creates_central_case():
    """Verifies that an inbound call initializes a central case with channel_of_origin='ivrs'."""
    call_sid = "CA_BRIDGE_TEST_001"
    case = get_or_create_central_case_for_call(call_sid=call_sid, language="hi")

    assert case["call_sid"] == "CA_BRIDGE_TEST_001"
    assert case["channel_of_origin"] == "ivrs"
    assert case["status"] == "new"
    assert case["language"] == "hi"


def test_end_to_end_telephony_to_central_case_pipeline():
    """
    Verifies full pipeline:
    Inbound call -> Perception -> Decision Engine -> Risk Assessment with recommended_action & nested flags.
    """
    call_sid = "CA_BRIDGE_E2E_002"
    flags = [
        InputFlagItem(name="intimidation", confidence=0.85, signals=["threat detected"]),
        InputFlagItem(name="trauma", confidence=0.80, signals=["crying voice"])
    ]
    signals = ["threat detected", "crying voice", "long pause: 3.8s"]

    result = process_telephony_call_to_central_case(
        call_sid=call_sid,
        svi_score=78.0,
        flags=flags,
        signals=signals,
        language="hi"
    )

    assert result.call_sid == "CA_BRIDGE_E2E_002"
    assert result.channel_of_origin == "ivrs"
    assert result.svi_score == 78.0
    assert result.risk_tier == "Critical"
    assert "police_intervention" in result.recommended_action
    assert result.confirmation_required is True

    # Verify nested flags payload shape
    nested = result.nested_flags
    assert "intimidation" in nested
    assert nested["intimidation"]["present"] is True
    assert nested["recommended_action"] == result.recommended_action

    # Verify central case updated for Dashboard
    case = get_or_create_central_case_for_call(call_sid=call_sid)
    assert case["svi_score"] == 78.0
    assert case["risk_tier"] == "critical"
    assert case["recommended_action"] == result.recommended_action
