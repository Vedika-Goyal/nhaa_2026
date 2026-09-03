# 📥 Agentic Decision Engine — Perception Input Contract

> **Target Consumer:** Aatmman's Agentic Decision Engine (`app/agent`)  
> **Source Producer:** Vedika's AI Perception Layer (`perception/`)  
> **Schema Module:** `app.agent.schemas.PerceptionInputContract`

---

## 🌟 Overview

The `PerceptionInputContract` defines the stable Pydantic input contract for consuming multi-modal perception outputs (Speech-to-Text transcript, Speech Emotion Recognition, acoustic bio-signals, and text distress classifications) into the Agentic Decision Engine.

> **Non-Clinical Boundary Notice:**  
> The input flags (`trauma`, `fear`, `suicidal_ideation`, `intimidation`, etc.) represent computational risk indicators extracted from speech and text signals. They **do not** constitute clinical or medical diagnoses.

---

## 📐 Schema Specification & Validation Rules

### 1. `InputSVIResult`
- **`score`**: Float between `0.0` and `100.0` (validated via `@field_validator`).
- **`risk_tier`**: Optional perception risk tier string e.g. `"Low"`, `"Moderate"`, `"High"`, `"Critical"`.

### 2. `InputFlagItem` (List Item Representation)
- **`name`**: Non-empty string key (e.g. `"intimidation"`, `"suicidal_ideation"`, `"trauma"`).
- **`confidence`**: Float between `0.0` and `1.0` (validated via `@field_validator`).
- **`signals`**: List of non-empty string evidence descriptions e.g. `["Keyword match: 'जान से मार'", "long pause: 3.8s"]`.
- **`source`**: List of validated source modalities e.g. `["audio"]`, `["text"]`, `["speech"]`, `["multimodal"]`.

### 3. `InputLanguageMetadata`
- **`code`**: ISO language code (min length 2) e.g. `"hi"`, `"en"`, `"mr"`, `"ta"`.
- **`name`**: Optional display name e.g. `"Hindi"`.
- **`confidence`**: Float between `0.0` and `1.0`.

### 4. `PerceptionInputContract`
- **`svi`**: `InputSVIResult` (Required)
- **`flags`**: `List[InputFlagItem]` (Required list representation)
- **`language`**: `Optional[InputLanguageMetadata]`
- **`stt_transcript`**: `Optional[str]`
- **`case_id`**: `Optional[Union[int, str]]`
- **`channel`**: `Optional[str]` (`"ivrs"`, `"portal"`, `"chatbot"`, `"mobile_app"`)
- **`model_metadata`**: `Optional[Dict[str, Any]]`

---

## 💡 How Vedika Imports & Uses This Contract

```python
from app.agent.schemas import PerceptionInputContract, InputSVIResult, InputFlagItem

# Instantiate input payload to pass into Agentic Decision Engine
input_payload = PerceptionInputContract(
    svi=InputSVIResult(score=79.0, risk_tier="Critical"),
    flags=[
        InputFlagItem(
            name="intimidation",
            confidence=0.90,
            signals=["Keyword match: 'जान से मार' in text"],
            source=["text"]
        )
    ],
    stt_transcript="मुझे बचाओ, मुझे जान से मारने की धमकी मिल रही है",
    channel="ivrs"
)
```
