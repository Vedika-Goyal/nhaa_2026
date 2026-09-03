"""
Unit Tests for Perception Input Contract (Subtask 1)
==============================================================================
Verifies validation rules for SVI score range [0, 100], confidence range [0, 1],
non-empty flag names, signal strings, and source modalities.
==============================================================================
"""

import json
import pathlib
import pytest
from pydantic import ValidationError

from app.agent.schemas import (
    PerceptionInputContract,
    InputSVIResult,
    InputFlagItem,
    InputLanguageMetadata,
)


def test_valid_perception_input_contract():
    """Verifies that a valid input payload passes schema validation."""
    payload = PerceptionInputContract(
        svi=InputSVIResult(score=79.0, risk_tier="Critical"),
        flags=[
            InputFlagItem(
                name="intimidation",
                confidence=0.90,
                signals=["Keyword match: 'जान से मार'"],
                source=["text"]
            ),
            InputFlagItem(
                name="extreme_vulnerability",
                confidence=0.65,
                signals=["long pause: 3.8s"],
                source=["audio", "text"]
            )
        ],
        language=InputLanguageMetadata(code="hi", name="Hindi", confidence=0.95),
        stt_transcript="मुझे बचाओ, मुझे जान से मारने की धमकी मिल रही है",
        case_id=101,
        channel="ivrs"
    )

    assert payload.svi.score == 79.0
    assert len(payload.flags) == 2
    assert payload.flags[0].name == "intimidation"
    assert payload.flags[0].confidence == 0.90
    assert "text" in payload.flags[0].source
    assert "audio" in payload.flags[1].source


def test_svi_score_range_validation():
    """Verifies that SVI scores outside [0, 100] raise ValidationError."""
    with pytest.raises(ValidationError):
        InputSVIResult(score=-5.0)

    with pytest.raises(ValidationError):
        InputSVIResult(score=105.0)


def test_confidence_range_validation():
    """Verifies that confidence scores outside [0.0, 1.0] raise ValidationError."""
    with pytest.raises(ValidationError):
        InputFlagItem(name="fear", confidence=-0.1, signals=["test"])

    with pytest.raises(ValidationError):
        InputFlagItem(name="fear", confidence=1.5, signals=["test"])


def test_non_empty_flag_name_validation():
    """Verifies that empty or whitespace-only flag names raise ValidationError."""
    with pytest.raises(ValidationError):
        InputFlagItem(name="", confidence=0.8, signals=["test"])

    with pytest.raises(ValidationError):
        InputFlagItem(name="   ", confidence=0.8, signals=["test"])


def test_signal_strings_validation():
    """Verifies that non-string signals or invalid types raise ValidationError."""
    flag = InputFlagItem(name="trauma", confidence=0.7, signals=["  flashback  ", "nightmare"])
    assert flag.signals == ["flashback", "nightmare"]


def test_source_modality_validation():
    """Verifies that invalid source modalities raise ValidationError."""
    with pytest.raises(ValidationError):
        InputFlagItem(name="trauma", confidence=0.7, source=["invalid_source"])


def test_load_example_json():
    """Verifies that example_perception_input.json loads and validates cleanly."""
    json_path = pathlib.Path(__file__).parent.parent / "app" / "agent" / "example_perception_input.json"
    assert json_path.exists(), f"Example JSON file not found at {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    contract = PerceptionInputContract(**data)
    assert contract.svi.score == 79.0
    assert len(contract.flags) == 3
    assert contract.channel == "ivrs"
