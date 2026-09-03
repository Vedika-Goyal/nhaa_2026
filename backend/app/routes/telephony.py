"""
Twilio Inbound Call Webhook Route Module (Subtask 13)
==============================================================================
NHAA 14566 / SIH 26093 - Telephony Integration
==============================================================================
Provides FastAPI endpoints for handling Twilio inbound voice webhooks.

Configurable Environment Variables:
- TWILIO_ACCOUNT_SID: Twilio Account SID
- TWILIO_AUTH_TOKEN: Twilio Auth Token (used for X-Twilio-Signature validation)
- TWILIO_PHONE_NUMBER: Provisioned Twilio Phone Number

TwiML Webhook Endpoint:
- POST /api/v1/telephony/voice
- POST /api/v1/telephony/inbound
==============================================================================
"""

import os
import hmac
import hashlib
import base64
from typing import Optional
from fastapi import APIRouter, Request, Response, Form, Header, HTTPException, status

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

    # Construct validation string: URL + sorted form parameters key+value
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

    Receives Twilio POST form data when a caller dials the helpline number.
    Returns valid TwiML XML instructing Twilio to greet the caller and hold/gather input.
    """
    config = get_twilio_env_config()
    form_data = await request.form()
    form_dict = dict(form_data)

    # Optional signature validation if AUTH_TOKEN is present
    if config["auth_token"] and x_twilio_signature:
        request_url = str(request.url)
        if not validate_twilio_signature(request_url, form_dict, x_twilio_signature, config["auth_token"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature verification failed."
            )

    caller_id = From or "Anonymous"
    call_sid = CallSid or "SIMULATED_CALL_SID"

    # Initial Basic TwiML Response (No ML connected yet, per Subtask 13)
    twiml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="hi-IN">
        राष्ट्रीय हेल्पलाइन 14566 में आपका स्वागत है। आपकी कॉल कनेक्ट की जा रही है।
    </Say>
    <Say voice="Polly.Aditi" language="en-IN">
        Welcome to the National Helpline 14566. Your call is being processed.
    </Say>
    <Pause length="2"/>
    <Hangup/>
</Response>"""

    return Response(content=twiml_content.strip(), media_type="application/xml")
