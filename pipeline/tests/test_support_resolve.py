from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
import main
from auth_guard import AuthUser


def _user(role="staff", dept="CSKH"):
    return AuthUser(id="u1", email="a@x.vn", role=role, department=dept)


def _db_with_task(status="open", team="CSKH"):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"assigned_team": team, "status": status}
    ]
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "t1", "status": "resolved"}
    ]
    return db


def test_support_resolve_staff_same_team_ok(monkeypatch):
    db = _db_with_task(status="open", team="CSKH")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    out = main.support_resolve("t1", main.SupportResolveReq(reply="Đã xử lý cho khách"), user=_user())
    assert out["status"] == "success"
    assert out["data"]["status"] == "resolved"


def test_support_resolve_other_team_forbidden(monkeypatch):
    db = _db_with_task(status="open", team="Vận hành")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.support_resolve("t1", main.SupportResolveReq(reply="x"), user=_user(dept="CSKH"))
    assert ei.value.status_code == 403


def test_support_resolve_already_resolved_conflict(monkeypatch):
    db = _db_with_task(status="resolved", team="CSKH")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.support_resolve("t1", main.SupportResolveReq(reply="x"), user=_user())
    assert ei.value.status_code == 409
