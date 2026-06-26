from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from auth_guard import AuthUser
from main import (
    update_draft_tasks,
    DraftTasksReq,
    approve_and_dispatch,
    ApproveDispatchReq,
)


def _user(role: str, department=None, uid="u1") -> AuthUser:
    return AuthUser(id=uid, email="u@example.com", role=role, department=department)


def test_update_draft_tasks_success():
    mock_db = MagicMock()
    mock_db.table().select().eq().limit().execute().data = [{"team": "IT", "approved": False}]
    mock_db.table().update().eq().eq().execute().data = [{"id": "r1", "team": "IT"}]

    with patch("main.get_supabase", return_value=mock_db):
        req = DraftTasksReq(suggested_tasks=[
            {"action": "Test", "deadline": "24h", "owner": "IT", "priority": "P1", "success_metric": "OK"}
        ])
        res = update_draft_tasks("r1", req, user=_user("manager", "IT"))
        assert res["status"] == "success"


def test_update_draft_tasks_forbidden():
    mock_db = MagicMock()
    mock_db.table().select().eq().limit().execute().data = [{"team": "IT", "approved": False}]

    with patch("main.get_supabase", return_value=mock_db):
        req = DraftTasksReq(suggested_tasks=[])
        with pytest.raises(HTTPException) as exc:
            update_draft_tasks("r1", req, user=_user("manager", "Vận hành"))
        assert exc.value.status_code == 403


def test_approve_and_dispatch_success():
    mock_db = MagicMock()
    mock_db.table().select().eq().limit().execute().data = [{
        "id": "r1", "team": "IT", "approved": False,
    }]
    mock_db.rpc().execute().data = 1

    with patch("main.get_supabase", return_value=mock_db):
        req = ApproveDispatchReq(suggested_tasks=[
            {"action": "Do this", "priority": "P2", "deadline": "48h"}
        ])
        res = approve_and_dispatch("r1", req, user=_user("manager", "IT"))
        assert res["status"] == "success"
        assert res["tasks_created"] == 1


def test_approve_and_dispatch_forbidden_other_team():
    mock_db = MagicMock()
    mock_db.table().select().eq().limit().execute().data = [{
        "id": "r1", "team": "IT", "approved": False,
    }]

    with patch("main.get_supabase", return_value=mock_db):
        req = ApproveDispatchReq(suggested_tasks=[{"action": "Do this"}])
        with pytest.raises(HTTPException) as exc:
            approve_and_dispatch("r1", req, user=_user("manager", "Vận hành"))
        assert exc.value.status_code == 403


def test_approve_and_dispatch_already_approved_conflict():
    mock_db = MagicMock()
    mock_db.table().select().eq().limit().execute().data = [{
        "id": "r1", "team": "IT", "approved": True,
    }]

    with patch("main.get_supabase", return_value=mock_db):
        req = ApproveDispatchReq(suggested_tasks=[{"action": "Do this"}])
        with pytest.raises(HTTPException) as exc:
            approve_and_dispatch("r1", user=_user("manager", "IT"), payload=req)
        assert exc.value.status_code == 409


def test_approve_and_dispatch_rollback_on_failure():
    """RPC dispatch là atomic ở tầng DB: nếu RPC lỗi thì báo cáo không được duyệt
    và endpoint trả lỗi (rollback do Postgres đảm bảo, không tạo task lẻ)."""
    mock_db = MagicMock()
    mock_db.table().select().eq().limit().execute().data = [{
        "id": "r1", "team": "IT", "approved": False,
    }]
    mock_db.rpc().execute.side_effect = Exception("DB Error")

    with patch("main.get_supabase", return_value=mock_db):
        req = ApproveDispatchReq(suggested_tasks=[
            {"action": "Do this"}, {"action": "Do that"}
        ])
        with pytest.raises(HTTPException) as exc:
            approve_and_dispatch("r1", req, user=_user("manager", "IT"))
        assert exc.value.status_code == 503
