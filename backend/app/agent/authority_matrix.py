"""
Authority Matrix Module for Agentic Decision Engine (Subtask 4)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Defines the explicit, configurable authority matrix enforcing role-based action
permissions against the real backend state pair:
    State = (status, current_level)

Supported 9 Roles (Matching OfficerRole enum in app/models.py):
- operator
- district
- state
- ministry
- police
- dlsa
- medical
- counselor
- witness_protection

Signature for Aditya:
    check_authority(role: str, action: str, status: str, current_level: str) -> bool
==============================================================================
"""

from typing import Set, Dict, Tuple
from app.models import OfficerRole, CaseStatus
from app.agent.state_machine import validate_state, VALID_LEVELS, VALID_STATUSES


# ── Exactly 9 Valid Roles ──────────────────────────────────────────────────
VALID_ROLES: Set[str] = {r.value for r in OfficerRole}

# ── Explicit Discovered Actions ────────────────────────────────────────────
VALID_ACTIONS: Set[str] = {
    "create_case",
    "view_case",
    "update_status",
    "escalate_case",
    "resolve_case",
    "close_case",
    "post_risk_assessment",
    "confirm_critical_dispatch",
    "dispatch_police",
    "provide_legal_aid",
    "provide_medical_aid",
    "provide_counseling",
    "provide_witness_protection",
    "action_responder_task",
}

# ── Role Level Hierarchy Ranks ──────────────────────────────────────────────
ROLE_RANK: Dict[str, int] = {
    "operator": 0,
    "district": 1,
    "state": 2,
    "ministry": 3,
    "police": 1,
    "dlsa": 1,
    "medical": 1,
    "counselor": 1,
    "witness_protection": 1,
}

LEVEL_RANK: Dict[str, int] = {
    "operator": 0,
    "police": 1,
    "district": 1,
    "state": 2,
    "ministry": 3,
}

# ── Explicit Configurable Authority Matrix ──────────────────────────────────
# Mapping: role -> Set[action]
ROLE_ACTION_PERMISSIONS: Dict[str, Set[str]] = {
    "operator": {
        "create_case",
        "view_case",
        "update_status",
        "escalate_case",
    },
    "district": {
        "view_case",
        "update_status",
        "escalate_case",
        "resolve_case",
        "close_case",
        "confirm_critical_dispatch",
    },
    "state": {
        "view_case",
        "update_status",
        "escalate_case",
        "resolve_case",
        "close_case",
    },
    "ministry": {
        "view_case",
        "update_status",
        "escalate_case",
        "resolve_case",
        "close_case",
    },
    "police": {
        "view_case",
        "dispatch_police",
        "action_responder_task",
    },
    "dlsa": {
        "view_case",
        "provide_legal_aid",
        "action_responder_task",
    },
    "medical": {
        "view_case",
        "provide_medical_aid",
        "action_responder_task",
    },
    "counselor": {
        "view_case",
        "provide_counseling",
        "action_responder_task",
    },
    "witness_protection": {
        "view_case",
        "provide_witness_protection",
        "action_responder_task",
    },
}


def check_authority(role: str, action: str, status: str, current_level: str) -> bool:
    """
    Evaluates whether a given officer role has authority to perform an action
    on a case in the specified state pair: (status, current_level).

    Parameters:
        role (str): Officer role e.g. 'district', 'operator', 'police'
        action (str): Intended action e.g. 'confirm_critical_dispatch', 'escalate_case'
        status (str): Case status e.g. 'new', 'in_progress', 'escalated'
        current_level (str): Administrative level e.g. 'operator', 'district', 'state'

    Returns:
        bool: True if authorized, False otherwise.

    Raises:
        ValueError: If role, action, or state pair (status, current_level) is invalid.
    """
    clean_role = str(role).strip().lower()
    clean_action = str(action).strip().lower()

    # 1. Validate Role
    if clean_role not in VALID_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Must be one of {sorted(list(VALID_ROLES))}. "
            "Do NOT use invented responder_type fields."
        )

    # 2. Validate Action
    if clean_action not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid action '{action}'. Must be one of {sorted(list(VALID_ACTIONS))}."
        )

    # 3. Validate State Pair (status, current_level)
    clean_status, clean_level = validate_state(status, current_level)

    # 4. Check closed case immutability (only viewing permitted)
    if clean_status == CaseStatus.closed.value and clean_action != "view_case":
        return False

    # 5. Check role action permissions
    permitted_actions = ROLE_ACTION_PERMISSIONS.get(clean_role, set())
    if clean_action not in permitted_actions:
        return False

    # 6. Check Administrative Level Hierarchy Authority
    role_r = ROLE_RANK.get(clean_role, 0)
    level_r = LEVEL_RANK.get(clean_level, 0)

    # Field responders can perform their specific actions if case is assigned to their level or active
    if clean_role in {"police", "dlsa", "medical", "counselor", "witness_protection"}:
        return True

    # Administrative roles (operator, district, state, ministry)
    # Can act on cases at their level rank or below
    if role_r < level_r and clean_action not in {"view_case"}:
        return False

    return True
