"""
Unit Tests for Authority Matrix (Subtask 4)
==============================================================================
Tests:
- Every role out of the 9 valid roles
- Valid authorized actions
- Unauthorized actions
- Invalid roles rejection
- Invalid actions rejection
- Invalid state pairs rejection
==============================================================================
"""

import pytest
from app.agent.authority_matrix import (
    check_authority,
    VALID_ROLES,
    VALID_ACTIONS,
)


def test_all_nine_roles_exist():
    """Verifies that exactly the 9 specified roles exist in VALID_ROLES."""
    expected_roles = {
        "operator",
        "district",
        "state",
        "ministry",
        "police",
        "dlsa",
        "medical",
        "counselor",
        "witness_protection",
    }
    assert VALID_ROLES == expected_roles


def test_valid_authorized_actions_for_roles():
    """Tests authorized actions for each of the 9 roles."""
    # 1. operator
    assert check_authority("operator", "create_case", "new", "operator") is True
    assert check_authority("operator", "escalate_case", "in_progress", "operator") is True

    # 2. district
    assert check_authority("district", "confirm_critical_dispatch", "escalated", "district") is True
    assert check_authority("district", "resolve_case", "in_progress", "district") is True

    # 3. state
    assert check_authority("state", "resolve_case", "in_progress", "state") is True
    assert check_authority("state", "escalate_case", "in_progress", "state") is True

    # 4. ministry
    assert check_authority("ministry", "view_case", "escalated", "ministry") is True
    assert check_authority("ministry", "close_case", "resolved", "ministry") is True

    # 5. police
    assert check_authority("police", "dispatch_police", "in_progress", "district") is True

    # 6. dlsa
    assert check_authority("dlsa", "provide_legal_aid", "in_progress", "district") is True

    # 7. medical
    assert check_authority("medical", "provide_medical_aid", "in_progress", "district") is True

    # 8. counselor
    assert check_authority("counselor", "provide_counseling", "in_progress", "district") is True

    # 9. witness_protection
    assert check_authority("witness_protection", "provide_witness_protection", "in_progress", "district") is True


def test_unauthorized_actions():
    """Tests that unauthorized action requests return False."""
    # Operator cannot confirm critical dispatch
    assert check_authority("operator", "confirm_critical_dispatch", "in_progress", "operator") is False

    # Operator cannot close a case
    assert check_authority("operator", "close_case", "in_progress", "operator") is False

    # Counselor cannot dispatch police
    assert check_authority("counselor", "dispatch_police", "in_progress", "district") is False

    # Medical officer cannot provide legal aid
    assert check_authority("medical", "provide_legal_aid", "in_progress", "district") is False

    # District officer cannot update closed case
    assert check_authority("district", "update_status", "closed", "district") is False


def test_invalid_role_rejection():
    """Verifies that invalid or invented role names raise ValueError."""
    with pytest.raises(ValueError) as exc:
        check_authority("invalid_role_name", "view_case", "new", "operator")
    assert "Invalid role" in str(exc.value)

    # Test invented responder_type
    with pytest.raises(ValueError) as exc:
        check_authority("responder_type_police", "view_case", "new", "operator")
    assert "Invalid role" in str(exc.value)


def test_invalid_action_rejection():
    """Verifies that invalid action names raise ValueError."""
    with pytest.raises(ValueError) as exc:
        check_authority("operator", "invalid_action_name", "new", "operator")
    assert "Invalid action" in str(exc.value)


def test_invalid_state_rejection():
    """Verifies that invalid status or current_level pair raises ValueError."""
    with pytest.raises(ValueError) as exc:
        check_authority("operator", "view_case", "pending_confirmation", "operator")
    assert "Invalid status" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        check_authority("operator", "view_case", "new", "invalid_level")
    assert "Invalid current_level" in str(exc.value)
