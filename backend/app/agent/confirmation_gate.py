"""
Critical Human-Confirmation Safety Gate (Subtask 7)
==============================================================================
NHAA 14566 / SIH 26093 - Agentic Decision Engine
==============================================================================
Enforces a hard backend safety gate making it structurally impossible to dispatch
any Critical-tier emergency action without explicit human officer confirmation.

Key Invariants:
1. Critical-tier cases ARE HELD in pending state until an authorized officer confirms.
2. Direct dispatch of an unconfirmed Critical action MUST FAIL.
3. Confirmation requires an authorized officer role (e.g. 'district', 'state', 'ministry').
4. Validates case existence, risk tier, confirmation pairing, revocation state, and state authority.
5. Emits an auditable event upon successful officer confirmation.
==============================================================================
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict

from app.models import RiskTier, OfficerRole, CaseStatus
from app.agent.authority_matrix import check_authority
from app.agent.state_machine import validate_state


class CriticalActionRecord(BaseModel):
    """
    Record of a Critical action prepared and held pending officer confirmation.
    """
    model_config = ConfigDict(protected_namespaces=())

    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: int = Field(..., description="ID of associated case")
    action: str = Field(..., description="Action name e.g. 'police_intervention', 'emergency_support'")
    risk_tier: str = Field(..., description="Must be 'critical'")
    svi_score: float = Field(..., ge=0.0, le=100.0)
    status: str = Field(default="pending_confirmation", description="Record dispatch status: 'pending_confirmation', 'confirmed', 'dispatched', 'revoked'")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CriticalConfirmationRecord(BaseModel):
    """
    Record of explicit officer confirmation for a Critical action.
    """
    model_config = ConfigDict(protected_namespaces=())

    confirmation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: int = Field(..., description="ID of associated case")
    record_id: str = Field(..., description="Associated CriticalActionRecord ID")
    confirmed_by: str = Field(..., min_length=1, description="Officer name / ID confirming the action")
    confirming_role: str = Field(..., description="Role of confirming officer e.g. 'district'")
    confirmed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    revoked: bool = Field(default=False, description="True if confirmation was revoked/invalidated")


class DispatchResult(BaseModel):
    """
    Outcome of dispatch_confirmed_action execution.
    """
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    case_id: int
    action: str
    confirmed_by: str
    dispatched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audit_event: Dict[str, Any]


# In-Memory Confirmation Registry for Decision Engine Gate Logic
_PENDING_CRITICAL_ACTIONS: Dict[int, List[CriticalActionRecord]] = {}
_CONFIRMATIONS: Dict[int, List[CriticalConfirmationRecord]] = {}


def reset_confirmation_registry():
    """Clears in-memory registry for fresh unit testing."""
    _PENDING_CRITICAL_ACTIONS.clear()
    _CONFIRMATIONS.clear()


def prepare_critical_action(
    case_id: int,
    action: str,
    risk_tier: str,
    svi_score: float
) -> CriticalActionRecord:
    """
    Prepares a Critical action and places it in pending_confirmation state.
    
    Raises:
        ValueError if risk_tier is not Critical.
    """
    tier_clean = str(risk_tier).strip().lower()
    if tier_clean != "critical":
        raise ValueError(f"prepare_critical_action can only be called for Critical tier cases, got '{risk_tier}'.")

    record = CriticalActionRecord(
        case_id=case_id,
        action=action,
        risk_tier="critical",
        svi_score=float(svi_score),
        status="pending_confirmation"
    )

    if case_id not in _PENDING_CRITICAL_ACTIONS:
        _PENDING_CRITICAL_ACTIONS[case_id] = []
    _PENDING_CRITICAL_ACTIONS[case_id].append(record)

    return record


def confirm_critical_action(
    case_id: int,
    confirmed_by: str,
    confirming_role: str,
    status: str,
    current_level: str,
    record_id: Optional[str] = None
) -> CriticalConfirmationRecord:
    """
    Confirms a pending Critical action by an authorized officer.

    Checks:
    1. Pending critical action record exists for case_id
    2. Confirming officer role is authorized via check_authority()
    3. Status/current_level state pair is valid
    """
    pending_records = _PENDING_CRITICAL_ACTIONS.get(case_id, [])
    if not pending_records:
        raise ValueError(f"No pending Critical action record found for case_id {case_id}.")

    target_record = None
    if record_id:
        for r in pending_records:
            if r.record_id == record_id and r.status == "pending_confirmation":
                target_record = r
                break
        if not target_record:
            raise ValueError(f"No matching pending Critical record with ID '{record_id}' found for case {case_id}.")
    else:
        target_record = pending_records[-1]

    # Validate state pair
    clean_status, clean_level = validate_state(status, current_level)

    # Check authority of confirming role to confirm critical dispatch
    is_authorized = check_authority(confirming_role, "confirm_critical_dispatch", clean_status, clean_level)
    if not is_authorized:
        raise PermissionError(
            f"Officer role '{confirming_role}' is not authorized to confirm Critical dispatch "
            f"in state ({clean_status}, {clean_level})."
        )

    confirmation = CriticalConfirmationRecord(
        case_id=case_id,
        record_id=target_record.record_id,
        confirmed_by=confirmed_by.strip(),
        confirming_role=confirming_role.strip().lower(),
        revoked=False
    )

    target_record.status = "confirmed"

    if case_id not in _CONFIRMATIONS:
        _CONFIRMATIONS[case_id] = []
    _CONFIRMATIONS[case_id].append(confirmation)

    return confirmation


def dispatch_confirmed_action(
    case_id: int,
    status: str,
    current_level: str,
    record_id: Optional[str] = None
) -> DispatchResult:
    """
    Dispatches a confirmed Critical action after verifying all 7 safety conditions:
    1. Case exists (record exists)
    2. Case is Critical
    3. Confirmation exists
    4. Confirming role is authorized
    5. Confirmation is tied to the correct case ID
    6. Confirmation has not been revoked/invalidated
    7. Action is allowed under current state
    
    MUST FAIL if attempted without explicit human officer confirmation.
    """
    pending_records = _PENDING_CRITICAL_ACTIONS.get(case_id, [])
    if not pending_records:
        raise ValueError(f"Case {case_id} does not exist or has no prepared Critical action.")

    target_record = None
    if record_id:
        for r in pending_records:
            if r.record_id == record_id:
                target_record = r
                break
    else:
        target_record = pending_records[-1]

    if not target_record:
        raise ValueError(f"Critical record '{record_id}' not found for case {case_id}.")

    # Condition 2: Case is Critical
    if target_record.risk_tier != "critical":
        raise ValueError(f"Case {case_id} is not Critical tier.")

    # Condition 3 & 5: Confirmation exists & tied to correct case
    confirmations = _CONFIRMATIONS.get(case_id, [])
    matching_conf = None
    for c in confirmations:
        if c.record_id == target_record.record_id:
            matching_conf = c
            break

    if not matching_conf:
        raise ValueError(
            f"DISPATCH BLOCKED: Critical action '{target_record.action}' for case {case_id} "
            "has NOT been confirmed by an authorized human officer."
        )

    # Condition 6: Confirmation has not been revoked
    if matching_conf.revoked:
        raise ValueError(f"DISPATCH BLOCKED: Confirmation for case {case_id} has been revoked/invalidated.")

    # Condition 4 & 7: Confirming role authorized under current state
    clean_status, clean_level = validate_state(status, current_level)
    if not check_authority(matching_conf.confirming_role, "confirm_critical_dispatch", clean_status, clean_level):
        raise PermissionError(f"DISPATCH BLOCKED: Confirming role '{matching_conf.confirming_role}' lacks authority in current state.")

    # Mark as dispatched
    target_record.status = "dispatched"

    audit_event = {
        "event": "critical_action_dispatched",
        "action": target_record.action,
        "case_id": case_id,
        "confirmed_by": matching_conf.confirmed_by,
        "confirming_role": matching_conf.confirming_role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {
            "svi_score": target_record.svi_score,
            "risk_tier": "critical",
            "state": (clean_status, clean_level)
        }
    }

    return DispatchResult(
        success=True,
        case_id=case_id,
        action=target_record.action,
        confirmed_by=matching_conf.confirmed_by,
        audit_event=audit_event
    )
