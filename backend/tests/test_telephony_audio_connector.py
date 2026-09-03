"""
Unit Tests for Telephony Audio Recording Connector (Subtask 15)
==============================================================================
Tests:
- Chunk metadata tracking (call_sid, recording_sid, case_id, chunk_number, timestamp)
- Incremental chunk numbering
- Integration with Vedika's perception pipeline (service.analyze)
- Audio buffer cleanup when TELEPHONY_AUDIO_RETENTION is False
- POST /api/v1/telephony/recording endpoint
==============================================================================
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agent.telephony_audio_connector import (
    process_twilio_recording_chunk,
    get_next_chunk_number,
    fetch_audio_bytes_from_url,
    TELEPHONY_AUDIO_RETENTION,
)

client = TestClient(app)


def test_incremental_chunk_numbering():
    """Verifies chunk numbers increment per call_sid."""
    call_sid = "CA_CHUNK_TEST_101"
    num1 = get_next_chunk_number(call_sid)
    num2 = get_next_chunk_number(call_sid)

    assert num1 == 1
    assert num2 == 2


def test_process_twilio_recording_chunk():
    """Verifies processing of a Twilio <Record> call audio chunk."""
    res = process_twilio_recording_chunk(
        call_sid="CA_REC_999",
        recording_sid="RE_999",
        recording_url="http://test/sample.wav",
        duration_seconds=12.5,
        case_id=301,
        language="hi",
        override_audio_bytes=b"RIFFmockwavdata0000000000"
    )

    assert res["status"] == "success"
    meta = res["chunk_metadata"]
    assert meta["call_sid"] == "CA_REC_999"
    assert meta["recording_sid"] == "RE_999"
    assert meta["case_id"] == 301
    assert meta["duration_seconds"] == 12.5
    assert meta["retention_cleaned"] is not TELEPHONY_AUDIO_RETENTION

    perc = res["perception_result"]
    assert "svi" in perc
    assert "score" in perc["svi"]


def test_telephony_recording_endpoint():
    """Simulates Twilio recording callback POST request to /api/v1/telephony/recording."""
    form_data = {
        "CallSid": "CA_ENDPOINT_TEST_55",
        "RecordingSid": "RE_ENDPOINT_TEST_55",
        "RecordingUrl": "http://test/chunk.wav",
        "RecordingDuration": "14.2"
    }

    response = client.post("/api/v1/telephony/recording", data=form_data)

    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")

    body_xml = response.text
    assert "<Response>" in body_xml
    assert "</Response>" in body_xml
