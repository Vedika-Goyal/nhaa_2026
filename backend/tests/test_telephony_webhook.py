"""
Unit Tests for Twilio Telephony Webhook Endpoint (Subtask 13)
==============================================================================
Tests:
- POST /api/v1/telephony/voice returns status 200
- Response content-type is application/xml
- Response body contains valid TwiML (<Response> and <Say> tags)
- Optional X-Twilio-Signature verification function testing
==============================================================================
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.telephony import validate_twilio_signature, get_twilio_env_config

client = TestClient(app)


def test_twilio_inbound_voice_webhook_mocked():
    """Simulates a Twilio webhook POST request and verifies valid TwiML XML response."""
    twilio_form_data = {
        "CallSid": "CA1234567890abcdef1234567890abcdef",
        "From": "+919876543210",
        "To": "+9114566",
        "CallStatus": "ringing",
        "ApiVersion": "2010-04-01"
    }

    response = client.post(
        "/api/v1/telephony/voice",
        data=twilio_form_data
    )

    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")

    body_xml = response.text
    assert "<Response>" in body_xml
    assert "</Response>" in body_xml
    assert "<Say" in body_xml
    assert "14566" in body_xml


def test_twilio_signature_validation_disabled_when_token_empty():
    """Verifies that signature validation passes when auth token is unconfigured (dev mode)."""
    is_valid = validate_twilio_signature(
        request_url="http://test/api/v1/telephony/voice",
        post_data={"CallSid": "123"},
        signature="dummy_signature",
        auth_token=""
    )

    assert is_valid is True
