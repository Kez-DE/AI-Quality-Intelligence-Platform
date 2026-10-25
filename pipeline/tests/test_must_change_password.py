"""US-077 / decision 0017: an admin-created account must replace its temporary password.

The flag lives in `app_metadata` (only the service role can write it), and the
backend enforces it: until the password is changed, every role-guarded route is
403, and only `/api/me` and `POST /api/me/password` answer. The database side
(`is_ops_staff()` reading the JWT claim) is checked on the local stack, not here.
"""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

import auth_guard
import mcp_auth
import users_admin
from auth_guard import AuthUser, get_current_user, require_admin, require_manager, require_ops_staff
from main import app
from tests._fakedb import FakeDB

NEW_PASSWORD = "Moi#Hon2026"


def _db_with_user(role="staff", flagged=True):
    db = FakeDB(profiles=[{"id": "u1", "email": "nv@local.test", "role": role, "department": "CSKH"}])
    user = SimpleNamespace(
        id="u1", email="nv@local.test",
        app_metadata={"provider": "email", "must_change_password": flagged},
    )
    updates: list[tuple[str, dict]] = []

    class _Admin:
        def update_user_by_id(self, uid, attrs):
            updates.append((uid, attrs))
            return SimpleNamespace(user=user)

    db.auth = SimpleNamespace(get_user=lambda _token: SimpleNamespace(user=user), admin=_Admin())
    db.updates = updates
    return db


def test_get_current_user_reads_the_flag_from_app_metadata(monkeypatch):
    monkeypatch.setattr(auth_guard, "get_supabase", lambda: _db_with_user(flagged=True))
    assert get_current_user("Bearer t").must_change_password is True
    monkeypatch.setattr(auth_guard, "get_supabase", lambda: _db_with_user(flagged=False))
    assert get_current_user("Bearer t").must_change_password is False


def test_user_metadata_flag_is_ignored(monkeypatch):
    """user_metadata is user-writable, so it must not be able to set or clear the flag."""
    db = _db_with_user(flagged=False)
    db.auth.get_user("t").user.user_metadata = {"must_change_password": True}
    monkeypatch.setattr(auth_guard, "get_supabase", lambda: db)
    assert get_current_user("Bearer t").must_change_password is False


@pytest.mark.parametrize("guard,role", [(require_ops_staff, "staff"), (require_manager, "manager"), (require_admin, "admin")])
def test_role_guards_refuse_a_flagged_account(guard, role):
    flagged = AuthUser(id="u1", email=None, role=role, department="CSKH", must_change_password=True)
    with pytest.raises(HTTPException) as exc:
        guard(flagged)
    assert exc.value.status_code == 403
    ok = AuthUser(id="u1", email=None, role=role, department="CSKH")
    assert guard(ok) is ok


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
def restore_overrides():
    prev = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(prev)


async def _call(method, path, **kw):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.request(method, path, **kw)


@pytest.mark.asyncio
async def test_flagged_account_gets_403_on_ops_routes_but_api_me_works(restore_overrides):
    _as(AuthUser(id="u1", email="nv@local.test", role="staff", department="CSKH", must_change_password=True))
    assert (await _call("GET", "/api/feedback/recent")).status_code == 403
    me = await _call("GET", "/api/me")
    assert me.status_code == 200
    assert me.json()["data"]["must_change_password"] is True


@pytest.mark.asyncio
async def test_change_password_clears_the_flag_via_the_admin_api(restore_overrides, monkeypatch, caplog):
    db = _db_with_user()
    monkeypatch.setattr(users_admin, "get_supabase", lambda: db)
    _as(AuthUser(id="u1", email="nv@local.test", role="staff", department="CSKH", must_change_password=True))
    caplog.set_level(logging.DEBUG)

    res = await _call("POST", "/api/me/password", json={"new_password": NEW_PASSWORD})

    assert res.status_code == 200, res.text
    assert db.updates == [("u1", {"password": NEW_PASSWORD, "app_metadata": {"must_change_password": False}})]
    assert NEW_PASSWORD not in res.text
    assert NEW_PASSWORD not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"new_password": "yeu"}, {"new_password": 123}, {}, {"new_password": "A" * 73}])
async def test_change_password_rejects_bad_input_without_echoing_it(restore_overrides, monkeypatch, body):
    db = _db_with_user()
    monkeypatch.setattr(users_admin, "get_supabase", lambda: db)
    _as(AuthUser(id="u1", email=None, role="staff", department="CSKH", must_change_password=True))

    res = await _call("POST", "/api/me/password", json=body)

    assert res.status_code == 400
    assert db.updates == []
    if isinstance(body.get("new_password"), str):
        assert body["new_password"] not in res.text


@pytest.mark.asyncio
async def test_change_password_needs_a_session(restore_overrides):
    app.dependency_overrides.pop(get_current_user, None)
    res = await _call("POST", "/api/me/password", json={"new_password": NEW_PASSWORD})
    assert res.status_code == 401


def test_mcp_refuses_a_flagged_jwt():
    db = _db_with_user(flagged=True)
    verifier = mcp_auth.SupabaseTokenVerifier(db=db)
    assert asyncio.run(verifier.verify_token("jwt")) is None
    db_ok = _db_with_user(flagged=False)
    assert asyncio.run(mcp_auth.SupabaseTokenVerifier(db=db_ok).verify_token("jwt")) is not None
