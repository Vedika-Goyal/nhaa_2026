"""
Unit Tests for AI-Officer Consistency Check (Subtask 9 / Phase 8)
==============================================================================
Tests:
- Matching tiers -> no mismatch flagged
- Adjacent tier difference (diff == 1) -> no mismatch flagged
- Multi-level tier mismatch (diff > 1) -> flagged for supervisor review
- Audit event payload generation ('ai_officer_tier_mismatch')
==============================================================================
"""

import pytest
from app.agent.consistency_check import check_ai_officer_consistency


def test_matching_tiers_no_mismatch():
    """Verifies that matching AI and Officer tiers produce no mismatch."""
    res = check_ai_officer_consistency(ai_tier="Critical", officer_tier="Critical", case_id=601)

    assert res.is_mismatch is False
    assert res.requires_supervisor_review is False
    assert res.tier_difference == 0
    assert res.audit_event["event"] == "ai_officer_tier_consistency_verified"


def test_adjacent_tier_diff_no_mismatch():
    """Verifies that 1-level tier differences (e.g. High vs Critical) are allowed."""
    res = check_ai_officer_consistency(ai_tier="High", officer_tier="Critical", case_id=602)

    assert res.is_mismatch is False
    assert res.requires_supervisor_review is False
    assert res.tier_difference == 1


def test_multi_level_mismatch_flagged():
    """Verifies that multi-level tier differences (e.g. Critical vs Low/Moderate) are flagged."""
    res = check_ai_officer_consistency(ai_tier="Critical", officer_tier="Low", case_id=603)

    assert res.is_mismatch is True
    assert res.requires_supervisor_review is True
    assert res.tier_difference == 3
    assert res.audit_event["event"] == "ai_officer_tier_mismatch"
    assert res.audit_event["requires_supervisor_review"] is True


def test_moderate_vs_critical_mismatch():
    """Verifies that Moderate vs Critical (diff == 2) triggers a mismatch flag."""
    res = check_ai_officer_consistency(ai_tier="Moderate", officer_tier="Critical", case_id=604)

    assert res.is_mismatch is True
    assert res.requires_supervisor_review is True
    assert res.tier_difference == 2
