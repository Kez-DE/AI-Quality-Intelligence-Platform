"""US-077 / decision 0017: the `guest` role is retired; a Pending account has no access.

A Pending account holds a valid Supabase JWT, so `get_current_user` accepts it.
What must stop it is the role guard on every route. These tests sweep the whole
app instead of listing endpoints, so a route added later without a role guard
fails here.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

import auth_guard
from auth_guard import AuthUser, get_current_user, require_admin, require_manager, require_ops_staff
from main import app
from tests.test_public_intake import iter_api_routes

PENDING = AuthUser(id="00000000-0000-0000-0000-0000000000p1", email="p@local.test", role="pending", department=None)

# The only routes a Pending account (or nobody at all) may reach.
OPEN_TO_PENDING = {
    "/",
    "/health",
    "/api/me",
    "/api/me/password",  # own password only; the way out of a temporary one
    "/api/public/feedback",
    "/api/public/feedback/{public_ref}",
}


@pytest.fixture
def as_pending():
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: PENDING
    yield
    if prev is None:
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = prev


def _protected_calls():
    for route in iter_api_routes(app):
        if route.path in OPEN_TO_PENDING:
            continue
        path = re.sub(r"\{[^}]+\}", "x", route.path)
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            yield method, path


PROTECTED = sorted(set(_protected_calls()))


def test_sweep_covers_the_endpoints_named_in_the_spec():
    named = {
        ("POST", "/api/feedback/submit"),
        ("POST", "/api/agent/chat"),
        ("GET", "/api/cockpit/overview"),
        ("GET", "/api/feedback/recent"),
        ("POST", "/api/admin/users"),
        ("GET", "/api/users"),
    }
    assert named <= set(PROTECTED)


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", PROTECTED)
async def test_pending_gets_403_everywhere_else(as_pending, method, path):
    """Role guards run before body and query validation, so an empty body is enough."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.request(method, path, json={})
    assert res.status_code == 403, f"{method} {path} -> {res.status_code} {res.text[:200]}"


@pytest.mark.asyncio
async def test_public_only_chat_does_not_open_a_door_for_pending(as_pending):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.post(
            "/api/agent/chat",
            json={"messages": [{"role": "user", "content": "xin chào"}], "public_only": True},
        )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_pending_can_still_ask_who_am_i(as_pending):
    """The Staff web needs /api/me to show the "đang chờ admin cấp quyền" screen."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.get("/api/me")
    assert res.status_code == 200
    assert res.json()["data"]["role"] == "pending"


@pytest.mark.parametrize("guard", [require_ops_staff, require_admin, require_manager])
def test_every_role_guard_rejects_pending(guard):
    with pytest.raises(HTTPException) as exc:
        guard(PENDING)
    assert exc.value.status_code == 403


def test_valid_roles_have_pending_not_guest():
    assert auth_guard.VALID_ROLES == {"admin", "manager", "staff", "pending"}
    assert "pending" not in auth_guard.OPS_ROLES


class _Profiles:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a):
        return self

    def eq(self, *_a):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _AuthDB:
    def __init__(self, profile_rows):
        self._rows = profile_rows
        self.auth = SimpleNamespace(get_user=lambda _t: SimpleNamespace(user=SimpleNamespace(id="u1", email="u@x")))

    def table(self, _name):
        return _Profiles(self._rows)


@pytest.mark.parametrize(
    "profile_rows",
    [
        [],                                        # JWT valid, no profile row
        [{"role": None, "department": None}],      # empty role
        [{"role": "guest", "department": None}],   # a stale value from before the migration
        [{"role": "superuser", "department": None}],
    ],
)
def test_missing_or_unknown_role_fails_closed_to_pending(monkeypatch, profile_rows):
    monkeypatch.setattr(auth_guard, "get_supabase", lambda: _AuthDB(profile_rows))
    user = auth_guard.get_current_user(authorization="Bearer t")
    assert user.role == "pending"
