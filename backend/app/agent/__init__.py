"""
NHAA Agentic Decision Engine - Core Package
"""

from app.agent.schemas import (
    PerceptionInputContract,
    InputFlagItem,
    InputSVIResult,
    InputLanguageMetadata,
)

from app.agent.state_machine import (
    validate_state,
    can_transition,
    transition_state,
    get_escalated_level,
    VALID_STATUSES,
    VALID_LEVELS,
)

from app.agent.risk_engine import (
    score_flags_to_tier,
    get_base_tier_from_svi,
    RiskTierDecision,
    LOW_TIER_MAX_SCORE,
    MODERATE_TIER_MAX_SCORE,
    HIGH_TIER_MAX_SCORE,
    CRITICAL_TIER_MIN_SCORE,
)

from app.agent.authority_matrix import (
    check_authority,
    VALID_ROLES,
    VALID_ACTIONS,
    ROLE_ACTION_PERMISSIONS,
)

from app.agent.action_recommender import (
    recommend_actions,
    ActionRecommendationResult,
    CANONICAL_ACTIONS,
)

from app.agent.explanation_generator import (
    generate_explanation,
    ExplanationResult,
    build_deterministic_fallback_explanation,
    SYSTEM_PROMPT_V1,
)

from app.agent.confirmation_gate import (
    prepare_critical_action,
    confirm_critical_action,
    dispatch_confirmed_action,
    reset_confirmation_registry,
    CriticalActionRecord,
    CriticalConfirmationRecord,
    DispatchResult,
)

from app.agent.silent_distress import (
    handle_silent_distress_signal,
    detect_dtmf_silent_signal,
    sanitize_transcript,
    SilentDistressResult,
    DEFAULT_DTMF_SEQUENCE,
)

from app.agent.consistency_check import (
    check_ai_officer_consistency,
    ConsistencyCheckResult,
    TIER_RANKS,
)

from app.agent.flags_formatter import (
    format_nested_flags,
    predict_sla_breach,
    SLAPredictionResult,
)

from app.agent.telephony_service import (
    generate_consent_twiml,
    process_telephony_dtmf,
    trigger_outbound_callback,
    get_or_create_call_session,
    TelephonyCallSession,
)

from app.agent.telephony_audio_connector import (
    process_twilio_recording_chunk,
    get_next_chunk_number,
    fetch_audio_bytes_from_url,
    TelephonyChunkMetadata,
)

from app.agent.telephony_central_case_bridge import (
    process_telephony_call_to_central_case,
    get_or_create_central_case_for_call,
    TelephonyCaseBridgeResult,
)

from app.agent.telephony_outbound_service import (
    send_followup_sms,
    send_followup_call,
    OutboundTriggerResult,
)

__all__ = [
    "PerceptionInputContract",
    "InputFlagItem",
    "InputSVIResult",
    "InputLanguageMetadata",
    "validate_state",
    "can_transition",
    "transition_state",
    "get_escalated_level",
    "VALID_STATUSES",
    "VALID_LEVELS",
    "score_flags_to_tier",
    "get_base_tier_from_svi",
    "RiskTierDecision",
    "LOW_TIER_MAX_SCORE",
    "MODERATE_TIER_MAX_SCORE",
    "HIGH_TIER_MAX_SCORE",
    "CRITICAL_TIER_MIN_SCORE",
    "check_authority",
    "VALID_ROLES",
    "VALID_ACTIONS",
    "ROLE_ACTION_PERMISSIONS",
    "recommend_actions",
    "ActionRecommendationResult",
    "CANONICAL_ACTIONS",
    "generate_explanation",
    "ExplanationResult",
    "build_deterministic_fallback_explanation",
    "SYSTEM_PROMPT_V1",
    "prepare_critical_action",
    "confirm_critical_action",
    "dispatch_confirmed_action",
    "reset_confirmation_registry",
    "CriticalActionRecord",
    "CriticalConfirmationRecord",
    "DispatchResult",
    "handle_silent_distress_signal",
    "detect_dtmf_silent_signal",
    "sanitize_transcript",
    "SilentDistressResult",
    "DEFAULT_DTMF_SEQUENCE",
    "check_ai_officer_consistency",
    "ConsistencyCheckResult",
    "TIER_RANKS",
    "format_nested_flags",
    "predict_sla_breach",
    "SLAPredictionResult",
    "generate_consent_twiml",
    "process_telephony_dtmf",
    "trigger_outbound_callback",
    "get_or_create_call_session",
    "TelephonyCallSession",
    "process_twilio_recording_chunk",
    "get_next_chunk_number",
    "fetch_audio_bytes_from_url",
    "TelephonyChunkMetadata",
    "process_telephony_call_to_central_case",
    "get_or_create_central_case_for_call",
    "TelephonyCaseBridgeResult",
    "send_followup_sms",
    "send_followup_call",
    "OutboundTriggerResult",
]
