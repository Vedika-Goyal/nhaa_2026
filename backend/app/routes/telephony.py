"""
Twilio Inbound Call Webhook Route Module (Subtask 13 & 14)
==============================================================================
NHAA 14566 / SIH 26093 - Telephony Integration
==============================================================================
Provides FastAPI endpoints for handling Twilio inbound voice webhooks,
consent notices, language selection, and keypad input processing.

Configurable Environment Variables:
- TWILIO_ACCOUNT_SID: Twilio Account SID
- TWILIO_AUTH_TOKEN: Twilio Auth Token (used for X-Twilio-Signature validation)
- TWILIO_PHONE_NUMBER: Provisioned Twilio Phone Number

TwiML Webhook Endpoints:
- POST /api/v1/telephony/voice
- POST /api/v1/telephony/consent
==============================================================================
"""

import os
import hmac
import hashlib
import base64
from typing import Optional
from fastapi import APIRouter, Request, Response, Form, Header, HTTPException, status

from app.agent.consent_service import (
    generate_consent_prompt_twiml,
    generate_consent_response_twiml,
    process_consent_digit_input,
    get_or_create_consent_session,
)

router = APIRouter(prefix="/telephony", tags=["telephony"])


def get_twilio_env_config() -> dict:
    """Returns Twilio configuration from environment variables without hardcoding."""
    return {
        "account_sid": os.environ.get("TWILIO_ACCOUNT_SID", "").strip(),
        "auth_token": os.environ.get("TWILIO_AUTH_TOKEN", "").strip(),
        "phone_number": os.environ.get("TWILIO_PHONE_NUMBER", "").strip(),
    }


def validate_twilio_signature(request_url: str, post_data: dict, signature: str, auth_token: str) -> bool:
    """
    Validates Twilio X-Twilio-Signature header HMAC SHA1 signature.
    Returns True if valid or if auth_token is unconfigured (development mode).
    """
    if not auth_token:
        return True

    data_str = request_url
    for k in sorted(post_data.keys()):
        data_str += f"{k}{post_data[k]}"

    computed_mac = hmac.new(
        auth_token.encode("utf-8"),
        data_str.encode("utf-8"),
        hashlib.sha1
    ).digest()
    expected_sig = base64.b64encode(computed_mac).decode("utf-8").strip()

    return hmac.compare_digest(expected_sig, signature.strip())


@router.post("/voice", response_class=Response)
@router.post("/inbound", response_class=Response)
async def twilio_inbound_voice_webhook(
    request: Request,
    CallSid: Optional[str] = Form(None),
    From: Optional[str] = Form(None),
    To: Optional[str] = Form(None),
    x_twilio_signature: Optional[str] = Header(None, alias="X-Twilio-Signature")
):
    """
    Twilio Inbound Call Webhook Endpoint.

    Receives Twilio POST form data on call connect.
    Returns valid TwiML playing the consent notice & gathering keypad input.
    """
    config = get_twilio_env_config()
    form_data = await request.form()
    form_dict = dict(form_data)

    if config["auth_token"] and x_twilio_signature:
        request_url = str(request.url)
        if not validate_twilio_signature(request_url, form_dict, x_twilio_signature, config["auth_token"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature verification failed."
            )

    call_sid = CallSid or "SIMULATED_CALL_SID"
    get_or_create_consent_session(call_sid)

    twiml_content = generate_consent_prompt_twiml(call_sid)
    return Response(content=twiml_content, media_type="application/xml")


@router.post("/consent", response_class=Response)
async def twilio_consent_digit_webhook(
    request: Request,
    CallSid: Optional[str] = Form(None),
    Digits: Optional[str] = Form(None),
    x_twilio_signature: Optional[str] = Header(None, alias="X-Twilio-Signature")
):
    """
    Processes caller keypad input for consent & language selection.
    - Press 1: Hindi (Consent Accepted)
    - Press 2: English (Consent Accepted)
    - Press 3: Marathi (Consent Accepted)
    - Press 9: Consent Declined -> AI Perception Pipeline BYPASSED completely.
    """
    config = get_twilio_env_config()
    form_data = await request.form()
    form_dict = dict(form_data)

    if config["auth_token"] and x_twilio_signature:
        request_url = str(request.url)
        if not validate_twilio_signature(request_url, form_dict, x_twilio_signature, config["auth_token"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature verification failed."
            )

    call_sid = CallSid or "SIMULATED_CALL_SID"
    digits = Digits or ""

    result = process_consent_digit_input(call_sid, digits)
    twiml_content = generate_consent_response_twiml(result)

    return Response(content=twiml_content, media_type="application/xml")
