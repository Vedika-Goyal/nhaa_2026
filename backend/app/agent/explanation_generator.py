"""
OpenRouter Explanation Generator Module (Subtask 6)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Generates short, signal-grounded, plain-language triage explanations for helpline
officers using OpenRouter LLM API (or deterministic fallback when offline/unauthenticated).

Rules:
- References actual available signals & evidence
- Explains why the risk tier and action were recommended
- Avoids generic phrases, medical/clinical diagnosis claims, and 'AI thinks' phrasing
- Versioned System Prompt constant
- Environment variables: OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_TIMEOUT
- Robust, deterministic fallback mechanism if API fails or key is unconfigured.
==============================================================================
"""

import json
import os
import urllib.request
import urllib.error
from typing import List, Dict, Any, Union, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.agent.risk_engine import _normalize_flags


# ── Versioned System Prompt Constant ───────────────────────────────────────
SYSTEM_PROMPT_V1 = """You are an expert helpline triage summary assistant for the National Helpline AI Architecture (NHAA 14566).
Your job is to generate a concise, objective, plain-language triage explanation for an authorized government helpline officer.

GUIDELINES:
1. Reference ONLY the exact risk signals and evidence provided (e.g. specific keywords, pause durations, pitch variability).
2. Explain clearly why the specific risk tier and recommended action were selected.
3. NEVER claim a clinical diagnosis, psychological assessment, or medical evaluation.
4. NEVER use generic fluff, internal chain-of-thought, or phrases like "the AI thinks", "the model believes", or "the algorithm decided".
5. Keep your response under 150 words. Be direct, professional, and factual.
"""

# ── Environment Variable Defaults ──────────────────────────────────────────
DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
DEFAULT_TIMEOUT = 10.0


class ExplanationResult(BaseModel):
    """
    Structured outcome of the explanation generation process.
    """
    model_config = ConfigDict(protected_namespaces=())

    explanation_text: str = Field(..., description="Short, plain-language explanation text for helpline officers")
    is_fallback: bool = Field(default=False, description="True if deterministic fallback was used instead of LLM call")
    model_used: str = Field(default="fallback", description="Name of LLM model or 'fallback'")


def build_deterministic_fallback_explanation(
    svi_score: float,
    risk_tier: str,
    flags: List[Dict[str, Any]],
    recommended_actions: str
) -> str:
    """
    Constructs a signal-grounded, deterministic fallback explanation string
    derived strictly from actual flags and signals without LLM generation.
    """
    score = float(svi_score)
    tier = str(risk_tier).capitalize()

    signal_evidences = []
    for f in flags:
        fname = f["name"]
        fconf = f["confidence"]
        signals_list = f.get("signals", [])
        if signals_list:
            sig_str = ", ".join(signals_list)
            signal_evidences.append(f"{fname.title()} (conf {fconf:.2f}: {sig_str})")
        else:
            signal_evidences.append(f"{fname.title()} (conf {fconf:.2f})")

    if signal_evidences:
        evidence_str = "; ".join(signal_evidences)
        return (
            f"Case classified as {tier} Risk (SVI Score: {score:.1f}). "
            f"Grounding evidence signals: {evidence_str}. "
            f"Recommended operational action: {recommended_actions}."
        )
    else:
        return (
            f"Case classified as {tier} Risk (SVI Score: {score:.1f}) based on baseline intake metrics. "
            f"Recommended operational action: {recommended_actions}."
        )


def generate_explanation(
    svi_score: float,
    risk_tier: str,
    flags: Union[List[Any], Dict[str, Any]],
    recommended_actions: str
) -> ExplanationResult:
    """
    Generates a concise explanation using OpenRouter LLM, falling back gracefully to a
    deterministic signal-grounded explanation if OpenRouter API is unconfigured or fails.
    """
    normalized_flags = _normalize_flags(flags)
    score = float(svi_score)
    tier = str(risk_tier).capitalize()
    actions_str = str(recommended_actions).strip()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model_name = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip()
    timeout_sec = float(os.environ.get("OPENROUTER_TIMEOUT", DEFAULT_TIMEOUT))

    # If API key is missing or unconfigured, use deterministic fallback
    if not api_key:
        fallback_text = build_deterministic_fallback_explanation(score, tier, normalized_flags, actions_str)
        return ExplanationResult(
            explanation_text=fallback_text,
            is_fallback=True,
            model_used="deterministic-fallback"
        )

    # Build User Prompt with exact signals
    signals_summary = []
    for f in normalized_flags:
        sig_text = ", ".join(f.get("signals", []))
        signals_summary.append(f"- {f['name']} (confidence {f['confidence']:.2f}): {sig_text}")

    signals_block = "\n".join(signals_summary) if signals_summary else "None"

    user_prompt = f"""Target Case Parameters:
- SVI Score: {score:.1f}
- Risk Tier: {tier}
- Recommended Actions: {actions_str}

Detected Evidence Signals:
{signals_block}

Generate the objective, signal-grounded triage explanation for the helpline officer.
"""

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_V1},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.2
    }

    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Vedika-Goyal/nhaa_2026",
                "X-Title": "NHAA 14566 Helpline Triage"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                res_data = json.loads(resp.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"].strip()
                if content:
                    # Sanitize forbidden phrases if any
                    content = content.replace("the AI thinks", "the intake signals indicate")
                    content = content.replace("AI model", "perception system")
                    return ExplanationResult(
                        explanation_text=content,
                        is_fallback=False,
                        model_used=model_name
                    )

    except Exception:
        # Graceful fallback on network timeout, 401, 500, or invalid json
        pass

    fallback_text = build_deterministic_fallback_explanation(score, tier, normalized_flags, actions_str)
    return ExplanationResult(
        explanation_text=fallback_text,
        is_fallback=True,
        model_used="deterministic-fallback"
    )
