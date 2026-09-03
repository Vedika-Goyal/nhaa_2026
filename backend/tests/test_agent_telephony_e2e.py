"""
Comprehensive End-to-End Test Suite for NHAA Agent & Telephony Integration (Subtask 20)
==============================================================================
NHAA 14566 / SIH 26093 - E2E Integration Test Harness
==============================================================================
Executes end-to-end integration tests covering:
1. Low Risk Tier Chain
2. Moderate Risk Tier Chain
3. High Risk Tier Chain
4. Critical Risk Tier Chain (Confirmation Gate Verification)
5. Live DTMF Silent Distress Signal Chain
6. AI-Officer Consistency Audit Discrepancy Check
7. Proactive Follow-Up Outbound Trigger (USP 4)
==============================================================================
"""

import time
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.agent.schemas import InputFlagItem
from app.agent.telephony_central_case_bridge import (
    process_telephony_call_to_central_case,
    get_or_create_central_case_for_call,
)
from app.agent.confirmation_gate import (
    confirm_critical_action,
    dispatch_confirmed_action,
    reset_confirmation_registry,
)
from app.agent.telephony_service import process_telephony_dtmf
from app.agent.consistency_check import check_ai_officer_consistency
from app.agent.telephony_outbound_service import send_followup_sms, send_followup_call
from app.agent.silent_distress import sanitize_transcript

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_registry():
    reset_confirmation_registry()
    yield
    reset_confirmation_registry()


def test_e2e_low_risk_chain():
    """Test Case 1: Low Risk Tier E2E Chain"""
    start_time = time.time()
    call_sid = "CA_E2E_LOW_001"
    flags = []
    signals = ["baseline complaint intake"]

    res = process_telephony_call_to_central_case(
        call_sid=call_sid,
        svi_score=18.0,
        flags=flags,
        signals=signals,
        language="hi"
    )
    elapsed_ms = (time.time() - start_time) * 1000.0

    assert res.risk_tier == "Low"
    assert res.svi_score == 18.0
    assert "standard_follow_up" in res.recommended_action
    assert res.confirmation_required is False
    assert res.nested_flags["recommended_action"] == res.recommended_action
    assert elapsed_ms < 500.0


def test_e2e_moderate_risk_chain():
    """Test Case 2: Moderate Risk Tier E2E Chain"""
    call_sid = "CA_E2E_MOD_002"
    flags = [InputFlagItem(name="trauma", confidence=0.65, signals=["crying tone"])]
    signals = ["crying tone"]

    res = process_telephony_call_to_central_case(
        call_sid=call_sid,
        svi_score=38.0,
        flags=flags,
        signals=signals,
        language="en"
    )

    assert res.risk_tier == "Moderate"
    assert "counselling" in res.recommended_action
    assert res.confirmation_required is False


def test_e2e_high_risk_chain():
    """Test Case 3: High Risk Tier E2E Chain with Intimidation Override"""
    call_sid = "CA_E2E_HIGH_003"
    flags = [InputFlagItem(name="intimidation", confidence=0.88, signals=["direct threat"])]
    signals = ["direct threat", "raised pitch"]

    res = process_telephony_call_to_central_case(
        call_sid=call_sid,
        svi_score=65.0,
        flags=flags,
        signals=signals,
        language="mr"
    )

    assert res.risk_tier == "High"
    assert "police_intervention" in res.recommended_action
    assert res.confirmation_required is False


def test_e2e_critical_risk_chain_and_confirmation_gate():
    """Test Case 4: Critical Risk Tier E2E Chain with Human Confirmation Gate"""
    call_sid = "CA_E2E_CRIT_004"
    flags = [InputFlagItem(name="suicidal_ideation", confidence=0.95, signals=["explicit ideation"])]
    signals = ["explicit ideation"]

    res = process_telephony_call_to_central_case(
        call_sid=call_sid,
        svi_score=85.0,
        flags=flags,
        signals=signals,
        language="hi"
    )

    assert res.risk_tier == "Critical"
    assert res.confirmation_required is True

    # 1. Direct dispatch without human confirmation MUST FAIL
    with pytest.raises(ValueError) as exc:
        dispatch_confirmed_action(case_id=res.case_id, status="escalated", current_level="district")
    assert "DISPATCH BLOCKED" in str(exc.value)

    # 2. Confirm action by authorized officer ('district')
    conf = confirm_critical_action(
        case_id=res.case_id,
        confirmed_by="District Magistrate Officer",
        confirming_role="district",
        status="escalated",
        current_level="district"
    )
    assert conf.confirmed_by == "District Magistrate Officer"

    # 3. Dispatch after human confirmation succeeds
    dispatch_res = dispatch_confirmed_action(case_id=res.case_id, status="escalated", current_level="district")
    assert dispatch_res.success is True
    assert dispatch_res.audit_event["event"] == "critical_action_dispatched"


def test_e2e_dtmf_silent_distress_chain():
    """Test Case 5: Covert DTMF Silent Distress Signal E2E Chain"""
    call_sid = "CA_E2E_DTMF_005"
    dtmf_res = process_telephony_dtmf(call_sid=call_sid, dtmf_digits="555", case_id=3005)

    assert dtmf_res["silent_signal_detected"] is True
    payload = dtmf_res["result"]
    assert payload["risk_tier"] == "critical"
    assert payload["svi_score"] == 90.0
    assert payload["confirmation_required"] is True

    # Visible transcript remains clean without trigger leak
    clean_transcript = sanitize_transcript("Spoke normally about application 555 info")
    assert "555" not in clean_transcript

    # TwiML route does NOT expose escalation to caller
    response = client.post("/api/v1/telephony/dtmf", data={"CallSid": call_sid, "Digits": "555"})
    assert response.status_code == 200
    assert "Critical" not in response.text
    assert "Emergency" not in response.text


def test_e2e_ai_officer_consistency_audit():
    """Test Case 6: AI-Officer Consistency Audit Check"""
    case_id = 3006
    audit_res = check_ai_officer_consistency(ai_tier="Critical", officer_tier="Low", case_id=case_id)

    assert audit_res.is_mismatch is True
    assert audit_res.requires_supervisor_review is True
    assert audit_res.tier_difference == 3
    assert audit_res.audit_event["event"] == "ai_officer_tier_mismatch"


def test_e2e_outbound_followup_trigger():
    """Test Case 7: Proactive Outbound Follow-Up Trigger (USP 4)"""
    case_id = 3007
    sms_res = send_followup_sms(to_phone_number="+919876543210", case_id=case_id)
    call_res = send_followup_call(to_phone_number="+919876543210", case_id=case_id)

    assert sms_res.success is True
    assert sms_res.provider_sid.startswith("SM")
    assert call_res.success is True
    assert call_res.provider_sid.startswith("CA")
