from unittest.mock import patch

import pytest
from fastapi import HTTPException

from auth_guard import AuthUser
from main import trigger_daily_report


def _user(role: str, department=None) -> AuthUser:
    return AuthUser(id="u1", email="u@example.com", role=role, department=department)


def test_manager_can_only_generate_own_department_report():
    with patch("agents.task_agent.generate_daily_report", return_value={"status": "success"}) as generate:
        trigger_daily_report(team="IT", user=_user("manager", "Vận hành"))

    generate.assert_called_once_with("Vận hành")


def test_admin_can_generate_selected_department_report():
    with patch("agents.task_agent.generate_daily_report", return_value={"status": "success"}) as generate:
        trigger_daily_report(team="IT", user=_user("admin"))

    generate.assert_called_once_with("IT")


def test_staff_cannot_generate_report():
    with pytest.raises(HTTPException) as exc:
        trigger_daily_report(team="IT", user=_user("staff", "IT"))

    assert exc.value.status_code == 403
