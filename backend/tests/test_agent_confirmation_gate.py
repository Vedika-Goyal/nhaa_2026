"""
Unit Tests for Critical Human-Confirmation Safety Gate (Subtask 7)
==============================================================================
Tests:
- Unconfirmed dispatch MUST FAIL (raises ValueError)
- Officer confirmation succeeds for authorized role ('district')
- Dispatched after confirmation succeeds
- Revoked confirmation blocks dispatch
- Unauthorized role confirmation raises PermissionError
- Audit event generation on dispatch
==============================================================================
"""

import pytest
from app.agent.confirmation_gate import (
    prepare_critical_action,
    confirm_critical_action,
    dispatch_confirmed_action,
    reset_confirmation_registry,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Resets in-memory confirmation registry before each test."""
    reset_confirmation_registry()
    yield
    reset_confirmation_registry()


def test_unconfirmed_dispatch_must_fail():
    """Step 1 Test: Attempting to dispatch a Critical action without confirmation MUST FAIL."""
    case_id = 999
    prepare_critical_action(
        case_id=case_id,
        action="police_intervention",
        risk_tier="critical",
        svi_score=88.5
    )

    # Attempting to dispatch without confirmation MUST FAIL
    with pytest.raises(ValueError) as exc:
        dispatch_confirmed_action(case_id=case_id, status="escalated", current_level="district")

    assert "DISPATCH BLOCKED" in str(exc.value)
    assert "has NOT been confirmed by an authorized human officer" in str(exc.value)


def test_full_confirmation_and_dispatch_flow():
    """Step 2 & 3 Test: Confirm -> Dispatch flow succeeds for authorized officer."""
    case_id = 1001

    # 1. Prepare critical action
    record = prepare_critical_action(
        case_id=case_id,
        action="police_intervention",
        risk_tier="critical",
        svi_score=92.0
    )
    assert record.status == "pending_confirmation"

    # 2. Confirm action by authorized officer (district officer)
    conf = confirm_critical_action(
        case_id=case_id,
        confirmed_by="Officer Vikram",
        confirming_role="district",
        status="escalated",
        current_level="district"
    )
    assert conf.confirmed_by == "Officer Vikram"
    assert conf.confirming_role == "district"
    assert conf.revoked is False

    # 3. Dispatch confirmed action succeeds
    result = dispatch_confirmed_action(
        case_id=case_id,
        status="escalated",
        current_level="district"
    )

    assert result.success is True
    assert result.action == "police_intervention"
    assert result.confirmed_by == "Officer Vikram"
    assert "audit_event" in result.model_dump()
    assert result.audit_event["event"] == "critical_action_dispatched"


def test_unauthorized_role_confirmation_fails():
    """Verifies that an unauthorized officer role cannot confirm Critical dispatch."""
    case_id = 1002
    prepare_critical_action(
        case_id=case_id,
        action="police_intervention",
        risk_tier="critical",
        svi_score=85.0
    )

    # Counselor role is unauthorized to confirm critical dispatch
    with pytest.raises(PermissionError) as exc:
        confirm_critical_action(
            case_id=case_id,
            confirmed_by="Counselor Ananya",
            confirming_role="counselor",
            status="escalated",
            current_level="district"
        )

    assert "not authorized to confirm Critical dispatch" in str(exc.value)


def test_revoked_confirmation_blocks_dispatch():
    """Verifies that a revoked/invalidated confirmation blocks dispatch."""
    case_id = 1003
    prepare_critical_action(
        case_id=case_id,
        action="emergency_support",
        risk_tier="critical",
        svi_score=80.0
    )

    conf = confirm_critical_action(
        case_id=case_id,
        confirmed_by="Officer Priya",
        confirming_role="district",
        status="escalated",
        current_level="district"
    )

    # Invalidate / revoke confirmation
    conf.revoked = True

    # Dispatch MUST FAIL
    with pytest.raises(ValueError) as exc:
        dispatch_confirmed_action(case_id=case_id, status="escalated", current_level="district")

    assert "revoked/invalidated" in str(exc.value)
