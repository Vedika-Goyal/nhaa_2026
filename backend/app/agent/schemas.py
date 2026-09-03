"""
Perception Input Contract Schema for Agentic Decision Engine
==============================================================================
NHAA 14566 / SIH 26093 - Decision Engine Module
==============================================================================
Defines the stable Pydantic input contract for consuming Perception Layer outputs
(Vedika's module) into Aatmman's Agentic Decision Engine.

Validation Rules:
- SVI score: Range [0.0, 100.0]
- Confidence: Range [0.0, 1.0]
- Flag names: Non-empty strings (whitespace stripped)
- Signals: List of non-empty strings
- Source modalities: Validated source values ('audio', 'text', 'speech', 'multimodal', 'audio_text')
- Non-clinical boundary: Flags represent perception risk signals, NOT medical diagnoses.
==============================================================================
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict


VALID_SOURCE_MODALITIES = {"audio", "text", "speech", "multimodal", "audio_text"}


class InputFlagItem(BaseModel):
    """
    Individual risk indicator flag received from the Perception Layer.
    Represented as a list item in the input payload.
    """
    name: str = Field(..., min_length=1, description="Risk indicator category identifier (non-empty)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    signals: List[str] = Field(default_factory=list, description="Evidence / raw signal strings")
    source: List[str] = Field(default_factory=lambda: ["text"], description="Source modalities e.g. ['audio'], ['text']")

    @field_validator("name")
    @classmethod
    def validate_non_empty_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Flag name must not be empty or whitespace-only.")
        return clean

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence score {v} out of valid range [0.0, 1.0].")
        return round(float(v), 4)

    @field_validator("signals")
    @classmethod
    def validate_signals_are_strings(cls, v: List[str]) -> List[str]:
        cleaned_signals = []
        for s in v:
            if not isinstance(s, str):
                raise ValueError(f"Signal entry '{s}' must be a string.")
            s_clean = s.strip()
            if s_clean:
                cleaned_signals.append(s_clean)
        return cleaned_signals

    @field_validator("source")
    @classmethod
    def validate_source_modalities(cls, v: List[str]) -> List[str]:
        cleaned = []
        for s in v:
            s_clean = s.lower().strip()
            if s_clean not in VALID_SOURCE_MODALITIES:
                raise ValueError(f"Source modality '{s}' must be one of {sorted(list(VALID_SOURCE_MODALITIES))}")
            cleaned.append(s_clean)
        return sorted(list(set(cleaned))) if cleaned else ["text"]


class InputLanguageMetadata(BaseModel):
    """Language metadata provided by the Perception Layer."""
    code: str = Field(..., min_length=2, description="ISO language code e.g. 'hi', 'en', 'mr', 'ta'")
    name: Optional[str] = Field(default=None, description="Language display name")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Language detection confidence score")


class InputSVIResult(BaseModel):
    """Stress Vulnerability Index (SVI) score and risk tier from Perception Layer."""
    score: float = Field(..., ge=0.0, le=100.0, description="Composite SVI score between 0 and 100")
    risk_tier: Optional[str] = Field(default=None, description="Calculated perception risk tier")

    @field_validator("score")
    @classmethod
    def validate_svi_range(cls, v: float) -> float:
        if v < 0.0 or v > 100.0:
            raise ValueError(f"SVI score {v} out of valid range [0.0, 100.0].")
        return round(float(v), 2)


class PerceptionInputContract(BaseModel):
    """
    Master Input Contract consumed by Aatmman's Agentic Decision Engine
    from Vedika's AI Perception Layer output.
    """
    model_config = ConfigDict(protected_namespaces=())

    svi: InputSVIResult = Field(..., description="SVI score container")
    flags: List[InputFlagItem] = Field(default_factory=list, description="List of detected risk indicator flags")
    language: Optional[InputLanguageMetadata] = Field(default=None, description="Language detection metadata")
    stt_transcript: Optional[str] = Field(default=None, description="Auto-transcribed speech text")
    case_id: Optional[Union[int, str]] = Field(default=None, description="Associated Case ID if available")
    channel: Optional[str] = Field(default="ivrs", description="Ingestion channel ('ivrs', 'portal', 'chatbot', 'mobile_app')")
    model_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Model metadata & execution metrics")
