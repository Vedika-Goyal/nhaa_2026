"""
Unit Tests for Decision Engine State Machine (Subtask 2)
==============================================================================
Tests:
- Valid state transitions
- Invalid state transitions
- Invalid enum values & invented statuses rejection
- current_level changes and hierarchy escalation
- Escalation scenarios
==============================================================================
"""

import pytest
from app.models import CaseStatus
from app.agent.state_machine import (
    validate_state,
    can_transition,
    transition_state,
    get_escalated_level,
)


def test_valid_state_validation():
    """Verifies that real status and current_level enums pass validation."""
    state = validate_state("new", "operator")
    assert state == ("new", "operator")

    state_district = validate_state("in_progress", "district")
    assert state_district == ("in_progress", "district")

    state_escalated = validate_state("escalated", "state")
    assert state_escalated == ("escalated", "state")


def test_invented_status_rejection():
    """Verifies that invented status names (e.g. pending_confirmation) raise ValueError."""
    invented_statuses = [
        "pending_district_approval",
        "pending_confirmation",
        "waiting_for_approval",
        "under_review",
        "pending_dispatch"
    ]

    for inv in invented_statuses:
        with pytest.raises(ValueError) as exc:
            validate_state(inv, "district")
        assert "Invalid status" in str(exc.value)


def test_invalid_level_rejection():
    """Verifies that invalid or unknown current_level values raise ValueError."""
    with pytest.raises(ValueError) as exc:
        validate_state("new", "invalid_level_name")
    assert "Invalid current_level" in str(exc.value)


def test_valid_transitions():
    """Tests legitimate case state progression and escalation transitions."""
    # 1. New -> In Progress
    assert can_transition(("new", "operator"), ("in_progress", "operator")) is True

    # 2. In Progress -> Escalated to District
    assert can_transition(("in_progress", "operator"), ("escalated", "district")) is True

    # 3. Escalated District -> In Progress District
    assert can_transition(("escalated", "district"), ("in_progress", "district")) is True

    # 4. In Progress District -> Escalated State
    assert can_transition(("in_progress", "district"), ("escalated", "state")) is True

    # 5. Escalated State -> In Progress State
    assert can_transition(("escalated", "state"), ("in_progress", "state")) is True

    # 6. In Progress State -> Resolved State
    assert can_transition(("in_progress", "state"), ("resolved", "state")) is True

    # 7. Resolved State -> Closed State
    assert can_transition(("resolved", "state"), ("closed", "state")) is True


def test_invalid_transitions():
    """Tests illegal state transitions (e.g. closed -> new, reverse escalation)."""
    # Closed -> New is illegal
    assert can_transition(("closed", "district"), ("new", "district")) is False

    # Closed -> In Progress is illegal
    assert can_transition(("closed", "district"), ("in_progress", "district")) is False

    # Resolved -> In Progress is illegal
    assert can_transition(("resolved", "district"), ("in_progress", "district")) is False

    # Illegal jump to unhandled non-escalation levels
    assert can_transition(("in_progress", "operator"), ("escalated", "ministry")) is True  # Higher level escalation valid


def test_transition_execution_and_raising():
    """Verifies transition_state executes valid transitions and raises ValueError on illegal ones."""
    # Valid transition returns new state
    new_state = transition_state(("new", "operator"), ("in_progress", "operator"))
    assert new_state == ("in_progress", "operator")

    escalated = transition_state(("in_progress", "operator"), ("escalated", "district"))
    assert escalated == ("escalated", "district")

    # Illegal transition raises ValueError
    with pytest.raises(ValueError) as exc:
        transition_state(("closed", "district"), ("new", "district"))
    assert "Illegal state transition" in str(exc.value)


def test_escalation_path_hierarchy():
    """Verifies level hierarchy escalation progression."""
    assert get_escalated_level("operator") == "district"
    assert get_escalated_level("district") == "state"
    assert get_escalated_level("state") == "ministry"
    assert get_escalated_level("police") == "district"
    assert get_escalated_level("ministry") == "ministry"
