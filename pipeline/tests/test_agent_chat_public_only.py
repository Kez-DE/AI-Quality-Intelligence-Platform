"""Cờ public_only của /api/agent/chat ép trợ lý về TẦNG CÔNG KHAI (Public FAQ/CSKH).

Bối cảnh: widget trợ lý ở trang chủ/landing gửi public_only=true để KHÔNG lộ dữ liệu nội bộ,
kể cả khi một tài khoản ops/admin đang đăng nhập. Cờ này chỉ HẠ quyền, không bao giờ nâng quyền.

Kiểm chứng ở tầng routing: khi public_only=true, run_chat_agent được gọi với
PUBLIC_TOOLS_DEFINITIONS (chỉ submit_feedback) + execute_fn riêng của tầng công khai — không có bộ tool
nội bộ; khi không có cờ, admin vẫn nhận đủ bộ tool OPS như bình thường.
"""
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

import main
from main import app
from auth_guard import get_current_user, AuthUser
from agent.chat_tools import PUBLIC_TOOLS_DEFINITIONS, tools_for_role

_FAKE_AGENT_RESULT = {"content": "ok", "provider": "mock", "model": "mock"}


def _override_user(user: AuthUser):
    """Ép get_current_user trả về `user`; trả về callable khôi phục trạng thái cũ."""
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: user

    def restore():
        if prev is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = prev

    return restore


@pytest.mark.asyncio
async def test_public_only_forces_public_tier_for_admin():
    admin = AuthUser(id="admin_public_only", email="a@test.com", role="admin", department="")
    restore = _override_user(admin)
    try:
        with patch.object(main, "run_chat_agent", return_value=dict(_FAKE_AGENT_RESULT)) as mock_run, \
                patch("agent.public_kb.search_public_knowledge", return_value=[]), \
                patch("agent.public_kb.format_public_for_prompt", return_value=""):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/agent/chat",
                    json={
                        "messages": [{"role": "user", "content": "khu vực nào đang nóng nhất?"}],
                        "public_only": True,
                    },
                )
        assert resp.status_code == 200, resp.text
        assert mock_run.call_count == 1
        _, kwargs = mock_run.call_args
        # Tầng công khai: CHỈ bộ tool công khai (submit_feedback) — không có tool nội bộ.
        assert kwargs.get("tools_override") == PUBLIC_TOOLS_DEFINITIONS
        assert kwargs.get("tools_override") != tools_for_role("admin")
        # Không scope kiểu ops; dùng execute_fn riêng của tầng công khai.
        assert kwargs.get("scope_team") is None
        assert kwargs.get("execute_fn") is not None
    finally:
        restore()


@pytest.mark.asyncio
async def test_admin_without_public_only_keeps_ops_tier():
    admin = AuthUser(id="admin_ops_tier", email="a@test.com", role="admin", department="")
    restore = _override_user(admin)
    try:
        with patch.object(main, "run_chat_agent", return_value=dict(_FAKE_AGENT_RESULT)) as mock_run, \
                patch.object(main, "build_agent_system_prompt", return_value="sys"), \
                patch.object(main, "build_agent_data_context", return_value="ctx"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/agent/chat",
                    json={"messages": [{"role": "user", "content": "tổng quan hệ thống hôm nay"}]},
                )
        assert resp.status_code == 200, resp.text
        assert mock_run.call_count == 1
        _, kwargs = mock_run.call_args
        # Admin bình thường: đủ bộ tool OPS, KHÁC bộ tool công khai.
        assert kwargs.get("tools_override") == tools_for_role("admin")
        assert kwargs.get("tools_override") != PUBLIC_TOOLS_DEFINITIONS
    finally:
        restore()


@pytest.mark.asyncio
async def test_public_only_forces_public_tier_for_staff():
    """Cờ chỉ HẠ quyền: staff có phòng gửi public_only=true cũng về tầng công khai."""
    staff = AuthUser(id="staff_public_only", email="s@test.com", role="staff", department="CSKH")
    restore = _override_user(staff)
    try:
        with patch.object(main, "run_chat_agent", return_value=dict(_FAKE_AGENT_RESULT)) as mock_run, \
                patch("agent.public_kb.search_public_knowledge", return_value=[]), \
                patch("agent.public_kb.format_public_for_prompt", return_value=""):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/agent/chat",
                    json={
                        "messages": [{"role": "user", "content": "cách gửi phản hồi?"}],
                        "public_only": True,
                    },
                )
        assert resp.status_code == 200, resp.text
        _, kwargs = mock_run.call_args
        assert kwargs.get("tools_override") == PUBLIC_TOOLS_DEFINITIONS
        assert kwargs.get("scope_team") is None
    finally:
        restore()
