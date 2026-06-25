import pytest
from fastapi import HTTPException

from main import _assert_transition, ALLOWED_TASK_TRANSITIONS


def test_open_to_assigned_ok():
    _assert_transition("open", "assigned")


def test_assigned_to_in_progress_ok():
    _assert_transition("assigned", "in_progress")


def test_pending_review_to_resolved_ok():
    _assert_transition("pending_review", "resolved")


def test_pending_review_to_in_progress_ok():
    _assert_transition("pending_review", "in_progress")


def test_same_state_is_noop():
    _assert_transition("in_progress", "in_progress")


def test_open_to_resolved_rejected():
    with pytest.raises(HTTPException) as exc:
        _assert_transition("open", "resolved")
    assert exc.value.status_code == 400


def test_table_has_reassign_paths():
    assert ("in_progress", "assigned") in ALLOWED_TASK_TRANSITIONS
