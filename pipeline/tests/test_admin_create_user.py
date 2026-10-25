"""US-077 / decision 0017: only an admin creates Staff accounts.

Self sign-up is gone, so `POST /api/admin/users` is the one way in. The risks it
carries are a weak temporary password, a duplicate account, a created account
with no audit trail, and the temporary password leaking into a response or log.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from supabase_auth.errors import AuthApiError

import users_admin
from auth_guard import AuthUser, get_current_user
from main import app
from tests._fakedb import FakeDB

ADMIN = AuthUser(id="admin-1", email="admin@local.test", role="admin", department=None)
TEMP_PASSWORD = "Tam#Thoi2026"

BODY = {
    "email": "Nhan.Vien@Local.Test ",
    "full_name": "Nhân Viên Mới",
    "role": "staff",
    "department": "CSKH",
    "temp_password": TEMP_PASSWORD,
}


class _FakeAdmin:
    """auth.admin double. create_user fires the handle_new_user trigger's effect:
    a profile row with role 'guest' (decision 0018: every sign-up after the first)."""

    def __init__(self, db: FakeDB, existing_emails=()):
        self._db = db
        self.existing = set(existing_emails)
        self.created: list[dict] = []
        self.deleted: list[str] = []

    def create_user(self, attributes):
        if attributes["email"] in self.existing:
            raise AuthApiError(
                "A user with this email address has already been registered", 422, "email_exists"
            )
        self.created.append(attributes)
        uid = f"new-{len(self.created)}"
        self.existing.add(attributes["email"])
        self._db.tables.setdefault("profiles", []).append(
            {"id": uid, "email": attributes["email"], "role": "guest", "department": None}
        )
        return SimpleNamespace(user=SimpleNamespace(id=uid, email=attributes["email"]))

    def delete_user(self, uid):
        self.deleted.append(uid)


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB(profiles=[], audit_logs=[])
    fake.auth = SimpleNamespace(admin=_FakeAdmin(fake, existing_emails={"taken@local.test"}))
    monkeypatch.setattr(users_admin, "get_supabase", lambda: fake)
    return fake


def _as(user):
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: user

    def restore():
        if prev is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = prev

    return restore


@pytest.fixture
def as_admin():
    restore = _as(ADMIN)
    yield
    restore()


async def post(body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post("/api/admin/users", json=body)


@pytest.mark.asyncio
async def test_creates_confirmed_account_with_forced_password_change(db, as_admin):
    res = await post(BODY)

    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert data == {"id": "new-1", "email": "nhan.vien@local.test", "role": "staff", "department": "CSKH"}

    [attrs] = db.auth.admin.created
    assert attrs["email"] == "nhan.vien@local.test"
    assert attrs["password"] == TEMP_PASSWORD
    assert attrs["email_confirm"] is True
    assert attrs["user_metadata"] == {"full_name": "Nhân Viên Mới"}
    # Server-only: the user cannot clear it with auth.updateUser.
    assert attrs["app_metadata"] == {"must_change_password": True}

    profile = db.tables["profiles"][0]
    assert (profile["role"], profile["department"]) == ("staff", "CSKH")


@pytest.mark.asyncio
async def test_writes_an_audit_log_without_the_password(db, as_admin):
    await post(BODY)

    [log] = db.tables["audit_logs"]
    assert log["action"] == "user_create"
    assert log["actor_id"] == ADMIN.id
    assert log["target_id"] == "new-1"
    assert log["target_email"] == "nhan.vien@local.test"
    assert log["details"] == {"role": "staff", "department": "CSKH"}
    assert TEMP_PASSWORD not in repr(log)


@pytest.mark.asyncio
async def test_department_is_optional(db, as_admin):
    res = await post({**BODY, "role": "admin", "department": None})
    assert res.status_code == 201
    assert res.json()["data"]["department"] is None


@pytest.mark.asyncio
async def test_duplicate_email_is_409(db, as_admin):
    res = await post({**BODY, "email": "taken@local.test"})
    assert res.status_code == 409
    assert db.tables["audit_logs"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password",
    [
        "Ab1!xyz",    # 7 characters
        "abcdef1!",   # no uppercase
        "ABCDEF1!",   # no lowercase
        "Abcdefg!",   # no digit
        "Abcdefg1",   # no special character
    ],
)
async def test_each_password_criterion_is_enforced(db, as_admin, password):
    """The same five checks the old sign-up form showed (auth.tsx validatePassword)."""
    res = await post({**BODY, "temp_password": password})
    assert res.status_code == 400
    assert password not in res.text
    assert db.auth.admin.created == []


def test_password_problems_matches_the_old_form():
    assert users_admin.password_problems("Abc123!x") == []
    assert len(users_admin.password_problems("")) == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "patch",
    [
        {"role": "pending"},    # a new account is created with a real role
        {"role": "guest"},
        {"role": "superuser"},
        {"department": "Phòng không tồn tại"},
        {"email": "not-an-email"},
        {"full_name": "   "},
    ],
)
async def test_invalid_fields_are_400(db, as_admin, patch):
    res = await post({**BODY, **patch})
    assert res.status_code == 400
    assert db.auth.admin.created == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["manager", "staff", "pending", "guest"])
async def test_non_admin_is_403(db, role):
    restore = _as(AuthUser(id="u", email=None, role=role, department="CSKH"))
    try:
        res = await post(BODY)
    finally:
        restore()
    assert res.status_code == 403
    assert db.auth.admin.created == []


@pytest.mark.asyncio
async def test_profile_failure_rolls_the_account_back(db, as_admin, monkeypatch):
    """A confirmed auth user whose role was never set is a half-made account."""
    original_table = db.table

    def table(name):
        t = original_table(name)
        if name == "profiles":
            t.update = lambda _payload: (_ for _ in ()).throw(RuntimeError("db down"))
        return t

    monkeypatch.setattr(db, "table", table)
    res = await post(BODY)

    assert res.status_code == 503
    assert db.auth.admin.deleted == ["new-1"]
    assert "đã huỷ tạo" in res.text


@pytest.mark.asyncio
async def test_failed_rollback_is_logged_and_reported_honestly(db, as_admin, monkeypatch, caplog):
    """If the rollback delete also fails, the admin must learn the account still exists."""
    original_table = db.table

    def table(name):
        t = original_table(name)
        if name == "profiles":
            t.update = lambda _payload: (_ for _ in ()).throw(RuntimeError("db down"))
        return t

    def delete_user(_uid):
        raise RuntimeError("auth down")

    monkeypatch.setattr(db, "table", table)
    monkeypatch.setattr(db.auth.admin, "delete_user", delete_user)
    caplog.set_level(logging.ERROR, logger="users_admin")
    res = await post(BODY)

    assert res.status_code == 503
    assert "đã huỷ tạo" not in res.text
    assert "vẫn tồn tại" in res.text
    assert "new-1" in caplog.text and "RuntimeError" in caplog.text
    assert TEMP_PASSWORD not in caplog.text


@pytest.mark.asyncio
async def test_password_never_appears_in_any_response_or_log(db, as_admin, caplog):
    caplog.set_level(logging.DEBUG)
    bodies = [
        BODY,                                        # success
        {**BODY, "email": "taken@local.test"},       # 409
        {**BODY, "role": "superuser"},               # 400 on another field
        {k: v for k, v in BODY.items() if k != "full_name"},  # missing field
        {**BODY, "email": 12345},                    # wrong type on another field
    ]
    for body in bodies:
        res = await post(body)
        assert TEMP_PASSWORD not in res.text, f"password echoed with {res.status_code}"

    assert TEMP_PASSWORD not in caplog.text


async def patch_role(user_id, role):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.patch(f"/api/users/{user_id}/role", json={"role": role})


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "manager", "staff", "pending"])
async def test_customer_account_role_never_changes(db, as_admin, role):
    """Decision 0018 §7: a Staff account only comes from the create-user form.
    'pending' is refused too, or guest -> pending -> staff (PATCH or
    bulk-approve) would promote a Customer account in two steps."""
    db.tables["profiles"].append({"id": "cust-1", "email": "khach@local.test", "role": "guest"})

    res = await patch_role("cust-1", role)

    assert res.status_code == 400
    assert "form Tạo tài khoản" in res.text
    assert db.tables["profiles"][-1]["role"] == "guest"
    assert db.tables["audit_logs"] == []


@pytest.mark.asyncio
async def test_bulk_approve_skips_customer_accounts(db, as_admin):
    db.tables["profiles"].append({"id": "cust-1", "email": "khach@local.test", "role": "guest"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.post("/api/users/bulk-approve", json={"user_ids": ["cust-1"], "role": "staff"})

    assert res.status_code == 200
    assert res.json()["data"]["approved_count"] == 0
    assert db.tables["profiles"][-1]["role"] == "guest"
