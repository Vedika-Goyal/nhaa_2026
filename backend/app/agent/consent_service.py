"""
Inbound Call Consent & Language Selection Service (Subtask 14)
==============================================================================
NHAA 14566 / SIH 26093 - Telephony Consent Module
==============================================================================
Manages mandatory caller consent interaction prior to AI perception analysis.

Rules:
1. Plays clear consent notice explaining automated triage analysis.
2. AI perception analysis MUST NOT run until consent is explicitly accepted.
3. Captures language choice ('hi', 'en', 'mr', 'ta') and consent status.
4. Stores minimal metadata (call_sid, consent_given, consent_timestamp, selected_language).
5. If consent is declined: AI pipeline is BYPASSED completely, routing to manual operator flow.
==============================================================================
"""

from datetime import datetime, timezone
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class CallConsentSession(BaseModel):
    """
    Session object tracking consent status and language selection for a call.
    Does NOT store unnecessary PII (no plain text name or identity data).
    """
    model_config = ConfigDict(protected_namespaces=())

    call_sid: str
    consent_given: Optional[bool] = Field(default=None, description="True if accepted, False if declined, None if pending")
    consent_timestamp: Optional[str] = Field(default=None, description="ISO 8601 timestamp of consent decision")
    selected_language: str = Field(default="hi", description="ISO language code e.g. 'hi', 'en', 'mr'")
    input_digits_history: list[str] = Field(default_factory=list, description="Audit log of digit inputs")
    ai_pipeline_allowed: bool = Field(default=False, description="True ONLY when consent_given is True")


# In-Memory Registry for Telephony Consent Sessions
_CONSENT_REGISTRY: Dict[str, CallConsentSession] = {}


def reset_consent_registry():
    """Resets in-memory consent registry for fresh unit tests."""
    _CONSENT_REGISTRY.clear()


def get_or_create_consent_session(call_sid: str) -> CallConsentSession:
    """Gets or initializes a CallConsentSession for a given call_sid."""
    clean_sid = str(call_sid).strip()
    if clean_sid not in _CONSENT_REGISTRY:
        _CONSENT_REGISTRY[clean_sid] = CallConsentSession(call_sid=clean_sid)
    return _CONSENT_REGISTRY[clean_sid]


def process_consent_digit_input(call_sid: str, digits: str) -> Dict[str, Any]:
    """
    Processes caller keypad input for consent and language selection.

    Keypad Mapping:
    - '1': Hindi (Consent Accepted -> AI Allowed)
    - '2': English (Consent Accepted -> AI Allowed)
    - '3': Marathi (Consent Accepted -> AI Allowed)
    - '9': Consent Declined -> AI Bypassed (Manual Operator Flow)
    """
    session = get_or_create_consent_session(call_sid)
    clean_digit = str(digits).strip()
    session.input_digits_history.append(clean_digit)

    timestamp_now = datetime.now(timezone.utc).isoformat()

    if clean_digit == "1":
        session.consent_given = True
        session.consent_timestamp = timestamp_now
        session.selected_language = "hi"
        session.ai_pipeline_allowed = True
        return {
            "status": "accepted",
            "language": "hi",
            "ai_allowed": True,
            "message": "Consent accepted for Hindi. Proceeding to AI triage flow."
        }

    elif clean_digit == "2":
        session.consent_given = True
        session.consent_timestamp = timestamp_now
        session.selected_language = "en"
        session.ai_pipeline_allowed = True
        return {
            "status": "accepted",
            "language": "en",
            "ai_allowed": True,
            "message": "Consent accepted for English. Proceeding to AI triage flow."
        }

    elif clean_digit == "3":
        session.consent_given = True
        session.consent_timestamp = timestamp_now
        session.selected_language = "mr"
        session.ai_pipeline_allowed = True
        return {
            "status": "accepted",
            "language": "mr",
            "ai_allowed": True,
            "message": "Consent accepted for Marathi. Proceeding to AI triage flow."
        }

    elif clean_digit == "9":
        session.consent_given = False
        session.consent_timestamp = timestamp_now
        session.ai_pipeline_allowed = False
        return {
            "status": "declined",
            "language": session.selected_language,
            "ai_allowed": False,
            "message": "Consent declined. AI perception pipeline bypassed. Transferring to manual queue."
        }

    else:
        # Invalid Digit Input
        return {
            "status": "invalid_input",
            "language": session.selected_language,
            "ai_allowed": False,
            "message": f"Invalid keypad input '{digits}'. Please press 1, 2, 3, or 9."
        }


def generate_consent_prompt_twiml(call_sid: str) -> str:
    """
    Generates TwiML XML playing consent notice and gathering keypad selection.
    """
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="hi-IN">
        राष्ट्रीय हेल्पलाइन 14566 में आपका स्वागत है। त्वरित सहायता के लिए स्वचालित एआई विश्लेषण का उपयोग किया जा सकता है।
    </Say>
    <Gather input="dtmf" numDigits="1" timeout="6" action="/api/v1/telephony/consent">
        <Say voice="Polly.Aditi" language="hi-IN">
            हिंदी के लिए 1 दबाएं। For English press 2. मराठी साठी 3 दाबा। एआई विश्लेषण से मना करने के लिए 9 दबाएं।
        </Say>
    </Gather>
    <Say voice="Polly.Aditi" language="hi-IN">कोई विकल्प नहीं चुना गया। आपकी कॉल मानव अधिकारी को ट्रांसफर की जा रही है।</Say>
    <Hangup/>
</Response>"""
    return twiml.strip()


def generate_consent_response_twiml(result: Dict[str, Any]) -> str:
    """
    Generates TwiML response based on consent outcome.
    """
    status_type = result["status"]
    lang = result.get("language", "hi")

    if status_type == "accepted":
        msg = "धन्यवाद। आपकी कॉल रिकॉर्डिंग और एआई विश्लेषण प्रारंभ किया जा रहा है।" if lang == "hi" else "Thank you. Your call is being processed."
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi">{msg}</Say>
    <Record maxLength="30" action="/api/v1/telephony/recording" playBeep="true"/>
</Response>""".strip()

    elif status_type == "declined":
        return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi">एआई विश्लेषण अस्वीकृत। आपकी कॉल बिना एआई के सीधे मानव हेल्पलाइन अधिकारी को ट्रांसफर की जा रही है।</Say>
    <Pause length="1"/>
    <Hangup/>
</Response>""".strip()

    else:  # invalid_input
        return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi">अमान्य विकल्प। कृपया सही विकल्प चुनें।</Say>
    <Redirect>/api/v1/telephony/voice</Redirect>
</Response>""".strip()
