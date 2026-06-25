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
