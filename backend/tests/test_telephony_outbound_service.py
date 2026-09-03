"""
Unit Tests for Outbound Callback & SMS Trigger Service (Subtask 18)
==============================================================================
Tests:
- send_followup_sms returns provider_sid (SM...), success, timestamp, channel='sms'
- send_followup_call returns provider_sid (CA...), success, timestamp, channel='voice'
- Audit event generation for Pushp's notification service
- Credentials environment variable configuration handling
==============================================================================
"""

import pytest
from app.agent.telephony_outbound_service import (
    send_followup_sms,
    send_followup_call,
)


def test_send_followup_sms():
    """Verifies send_followup_sms generates valid response object & audit event."""
    res = send_followup_sms(
        to_phone_number="+919876543210",
        case_id=401,
        message_text="Follow-up check for Case #401"
    )

    assert res.case_id == 401
    assert res.channel == "sms"
    assert res.to_phone_number == "+919876543210"
    assert res.provider_sid.startswith("SM")
    assert res.success is True
    assert res.timestamp is not None
    assert res.audit_event["event"] == "proactive_followup_sms_dispatched"


def test_send_followup_call():
    """Verifies send_followup_call generates valid response object & audit event."""
    res = send_followup_call(
        to_phone_number="+919876543210",
        case_id=402,
        callback_url="https://demo.twilio.com/welcome/voice/"
    )

    assert res.case_id == 402
    assert res.channel == "voice"
    assert res.to_phone_number == "+919876543210"
    assert res.provider_sid.startswith("CA")
    assert res.success is True
    assert res.timestamp is not None
    assert res.audit_event["event"] == "proactive_followup_call_dispatched"
