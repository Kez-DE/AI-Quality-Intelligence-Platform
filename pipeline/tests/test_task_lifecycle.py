import os
import sys
from unittest.mock import patch

import pytest
from fastapi import HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from _fakedb import FakeDB
from auth_guard import AuthUser
from main import (
    list_assignable_users,
    assign_task,
    accept_task,
    submit_completion_report,
    review_completion_report,
    AssignTaskReq,
    CompletionReportReq,
    ReviewReportReq,
)
# accept_task (Task 7) và list_task_events (Task 10) sẽ được thêm vào import này
# khi tới các task đó — chỉ import symbol đã tồn tại để test chạy được ngay.


def _user(role: str, dept=None, uid="u1") -> AuthUser:
    return AuthUser(id=uid, email=f"{uid}@x.com", role=role, department=dept)


def test_assignable_returns_staff_only():
    db = FakeDB(profiles=[
        {"id": "s1", "email": "s@x", "role": "staff", "department": "IT", "full_name": None},
        {"id": "m1", "email": "m@x", "role": "manager", "department": "IT", "full_name": None},
        {"id": "a1", "email": "a@x", "role": "admin", "department": "IT", "full_name": None},
    ])
    with patch("main.get_supabase", return_value=db):
        out = list_assignable_users(team=None, user=_user("manager", "IT"))
    assert {u["role"] for u in out["data"]} == {"staff"}


def _db_with_task(status="open", team="IT"):
    return FakeDB(
        tasks=[{"id": "t1", "assigned_team": team, "status": status, "owner_id": None}],
        profiles=[
            {"id": "s1", "email": "s@x", "role": "staff", "department": "IT", "full_name": "S"},
            {"id": "m1", "email": "m@x", "role": "manager", "department": "IT", "full_name": "M"},
        ],
        task_events=[],
    )


def test_staff_cannot_assign():
    db = _db_with_task()
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            assign_task("t1", AssignTaskReq(owner_id="s1"), user=_user("staff", "IT"))
    assert exc.value.status_code == 403


def test_assign_rejects_manager_owner():
    db = _db_with_task()
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            assign_task("t1", AssignTaskReq(owner_id="m1"), user=_user("manager", "IT"))
    assert exc.value.status_code == 400


def test_assign_sets_status_and_logs_event():
    db = _db_with_task()
    with patch("main.get_supabase", return_value=db):
        assign_task("t1", AssignTaskReq(owner_id="s1"), user=_user("manager", "IT"))
    task = db.tables["tasks"][0]
    assert task["status"] == "assigned"
    assert task["owner_id"] == "s1"
    assert any(e["action"] == "assigned" for e in db.tables["task_events"])


def test_accept_by_owner_moves_in_progress():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "assigned", "owner_id": "s1"}],
        task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        accept_task("t1", user=_user("staff", "IT", uid="s1"))
    assert db.tables["tasks"][0]["status"] == "in_progress"
    assert any(e["action"] == "accepted" for e in db.tables["task_events"])


def test_accept_by_non_owner_forbidden():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "assigned", "owner_id": "s1"}],
        task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            accept_task("t1", user=_user("staff", "IT", uid="s2"))
    assert exc.value.status_code == 403


def test_accept_open_task_invalid_transition():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "open", "owner_id": "s1"}],
        task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            accept_task("t1", user=_user("staff", "IT", uid="s1"))
    assert exc.value.status_code == 400


def test_submit_completed_sets_pending_review():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "in_progress", "owner_id": "s1"}],
        task_completion_reports=[], task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        submit_completion_report(
            "t1", CompletionReportReq(note="đã xử lý xong", completion_level="completed"),
            user=_user("staff", "IT", uid="s1"),
        )
    assert db.tables["tasks"][0]["status"] == "pending_review"
    assert len(db.tables["task_completion_reports"]) == 1
    assert any(e["action"] == "completion_submitted" for e in db.tables["task_events"])


def test_submit_partial_keeps_in_progress():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "in_progress", "owner_id": "s1"}],
        task_completion_reports=[], task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        submit_completion_report(
            "t1", CompletionReportReq(note="mới một phần", completion_level="partial"),
            user=_user("staff", "IT", uid="s1"),
        )
    assert db.tables["tasks"][0]["status"] == "in_progress"
