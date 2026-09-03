"""
Decision Engine State Machine Module (Subtask 2)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Implements state machine validation and transitions operating on the pair:
    State = (status, current_level)

Rules:
- status in {new, in_progress, escalated, resolved, closed}
- current_level in {operator, district, state, ministry, police}
- Strict enum validation rejecting invented statuses (e.g. pending_confirmation)
- Matching Vinit's backend PATCH /api/cases/{case_id} state transition model
==============================================================================
"""

from typing import Tuple, Set, Dict, Optional
from app.models import CaseStatus, OfficerRole


VALID_STATUSES: Set[str] = {s.value for s in CaseStatus}

# Supported current_level administrative levels
VALID_LEVELS: Set[str] = {
    "operator",
    "district",
    "state",
    "ministry",
    "police"
}

LEVEL_HIERARCHY: Dict[str, int] = {
    "operator": 0,
    "district": 1,
    "state": 2,
    "ministry": 3,
    "police": 1
}

LEVEL_ESCALATION_PATH: Dict[str, str] = {
    "operator": "district",
    "district": "state",
    "state": "ministry",
    "police": "district",
    "ministry": "ministry"
}


def validate_state(status: str, current_level: str) -> Tuple[str, str]:
    """
    Validates that (status, current_level) uses strictly valid backend enums.
    
    Raises:
        ValueError if status or current_level is invalid or invented.
    """
    clean_status = str(status).strip().lower()
    clean_level = str(current_level).strip().lower()

    if clean_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of {sorted(list(VALID_STATUSES))}. "
            "Invented status names like 'pending_district_approval' or 'pending_confirmation' are invalid."
        )

    if clean_level not in VALID_LEVELS:
        raise ValueError(
            f"Invalid current_level '{current_level}'. Must be one of {sorted(list(VALID_LEVELS))}."
        )

    return (clean_status, clean_level)


def can_transition(from_state: Tuple[str, str], to_state: Tuple[str, str]) -> bool:
    """
    Evaluates whether a state transition from from_state -> to_state is valid.
    
    State representation: (status, current_level)
    """
    try:
        from_status, from_level = validate_state(from_state[0], from_state[1])
        to_status, to_level = validate_state(to_state[0], to_state[1])
    except ValueError:
        return False

    # Same state is always trivially valid (no-op)
    if (from_status, from_level) == (to_status, to_level):
        return True

    # Terminal states (closed) cannot transition to new/in_progress
    if from_status == CaseStatus.closed.value:
        return False

    # Resolved states can only transition to closed
    if from_status == CaseStatus.resolved.value:
        return (to_status, to_level) in {
            (CaseStatus.closed.value, from_level),
            (CaseStatus.closed.value, to_level)
        }

    # Transition Rules:
    # 1. new -> in_progress (intake / assignment)
    if from_status == CaseStatus.new.value:
        if to_status == CaseStatus.in_progress.value:
            return True
        if to_status == CaseStatus.escalated.value and to_level == LEVEL_ESCALATION_PATH.get(from_level, from_level):
            return True
        if to_status in {CaseStatus.resolved.value, CaseStatus.closed.value}:
            return True
        return False

    # 2. in_progress -> escalated (escalation to higher level)
    if from_status == CaseStatus.in_progress.value and to_status == CaseStatus.escalated.value:
        target_expected_level = LEVEL_ESCALATION_PATH.get(from_level, from_level)
        return to_level == target_expected_level or LEVEL_HIERARCHY.get(to_level, 0) > LEVEL_HIERARCHY.get(from_level, 0)

    # 3. escalated -> in_progress (acknowledgment by escalated level officer)
    if from_status == CaseStatus.escalated.value and to_status == CaseStatus.in_progress.value:
        return True

    # 4. escalated -> escalated (further escalation to next level up)
    if from_status == CaseStatus.escalated.value and to_status == CaseStatus.escalated.value:
        return LEVEL_HIERARCHY.get(to_level, 0) > LEVEL_HIERARCHY.get(from_level, 0)

    # 5. in_progress -> resolved / closed
    if from_status in {CaseStatus.in_progress.value, CaseStatus.escalated.value} and to_status in {CaseStatus.resolved.value, CaseStatus.closed.value}:
        return True

    return False


def transition_state(from_state: Tuple[str, str], to_state: Tuple[str, str]) -> Tuple[str, str]:
    """
    Executes and validates state transition from_state -> to_state.
    
    Returns:
        New state pair (status, current_level)
        
    Raises:
        ValueError if the transition is illegal or enums are invalid.
    """
    from_status, from_level = validate_state(from_state[0], from_state[1])
    to_status, to_level = validate_state(to_state[0], to_state[1])

    if not can_transition((from_status, from_level), (to_status, to_level)):
        raise ValueError(
            f"Illegal state transition from ({from_status}, {from_level}) -> ({to_status}, {to_level})."
        )

    return (to_status, to_level)


def get_escalated_level(current_level: str) -> str:
    """Returns the next escalation level in the administrative hierarchy."""
    clean_level = str(current_level).strip().lower()
    if clean_level not in VALID_LEVELS:
        raise ValueError(f"Invalid current_level '{current_level}'.")
    return LEVEL_ESCALATION_PATH.get(clean_level, clean_level)
