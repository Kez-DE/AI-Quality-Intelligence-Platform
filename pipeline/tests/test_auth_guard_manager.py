import pytest
from fastapi import HTTPException

from auth_guard import require_manager, AuthUser


def _u(role: str) -> AuthUser:
    return AuthUser(id="u", email=None, role=role, department=None)


def test_manager_passes():
    assert require_manager(_u("manager")).role == "manager"


def test_admin_passes():
    assert require_manager(_u("admin")).role == "admin"


def test_staff_forbidden():
    with pytest.raises(HTTPException) as exc:
        require_manager(_u("staff"))
    assert exc.value.status_code == 403


def test_pending_forbidden():
    with pytest.raises(HTTPException) as exc:
        require_manager(_u("pending"))
    assert exc.value.status_code == 403
