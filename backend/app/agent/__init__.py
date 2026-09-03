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
]
