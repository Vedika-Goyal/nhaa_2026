"""
Unit Tests for OpenRouter Explanation Generator (Subtask 6)
==============================================================================
Tests:
- Deterministic fallback generation when OPENROUTER_API_KEY is unconfigured
- Signal-grounded evidence inclusion in fallback text
- Mocked OpenRouter API success case
- Graceful fallback on API error/timeout
- Absence of prohibited phrases ('the AI thinks', etc.)
==============================================================================
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from app.agent.explanation_generator import (
    generate_explanation,
    build_deterministic_fallback_explanation,
    SYSTEM_PROMPT_V1,
)


def test_deterministic_fallback_without_api_key(monkeypatch):
    """Verifies that unconfigured API key uses deterministic fallback."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    flags = [
        {"name": "intimidation", "confidence": 0.85, "signals": ["Keyword match: 'धमकी'"]}
    ]
    result = generate_explanation(
        svi_score=79.0,
        risk_tier="Critical",
        flags=flags,
        recommended_actions="police_intervention, legal_aid"
    )

    assert result.is_fallback is True
    assert result.model_used == "deterministic-fallback"
    assert "Intimidation" in result.explanation_text
    assert "Critical" in result.explanation_text
    assert "police_intervention" in result.explanation_text


def test_fallback_references_actual_signals():
    """Verifies that the fallback text references actual signals and contains no generic fluff."""
    flags = [
        {"name": "extreme_vulnerability", "confidence": 0.70, "signals": ["long pause: 3.8s"]}
    ]
    text = build_deterministic_fallback_explanation(
        svi_score=60.0,
        risk_tier="High",
        flags=flags,
        recommended_actions="counselling"
    )

    assert "Extreme_Vulnerability" in text or "Extreme_vulnerability" in text or "Extreme_Vulnerability" in text.title()
    assert "long pause: 3.8s" in text
    assert "the AI thinks" not in text
    assert "clinical diagnosis" not in text


def test_mocked_openrouter_api_success(monkeypatch):
    """Verifies successful LLM response when OPENROUTER_API_KEY is provided."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-mock-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": "Case assessed at Critical risk due to explicit intimidation signals (threat keywords detected). Urgent police intervention recommended."
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = generate_explanation(
            svi_score=85.0,
            risk_tier="Critical",
            flags=[{"name": "intimidation", "confidence": 0.90, "signals": ["threat"]}],
            recommended_actions="police_intervention"
        )

    assert result.is_fallback is False
    assert result.model_used == "meta-llama/llama-3.1-8b-instruct:free"
    assert "Critical risk" in result.explanation_text


def test_mocked_openrouter_api_error_fallback(monkeypatch):
    """Verifies that API errors gracefully trigger the deterministic fallback."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-mock-key")

    with patch("urllib.request.urlopen", side_effect=Exception("API Timeout or 500 Error")):
        result = generate_explanation(
            svi_score=75.0,
            risk_tier="Critical",
            flags=[{"name": "suicidal_ideation", "confidence": 0.85, "signals": ["help"]}],
            recommended_actions="emergency_support"
        )

    assert result.is_fallback is True
    assert result.model_used == "deterministic-fallback"
    assert "Critical" in result.explanation_text
    assert "emergency_support" in result.explanation_text
