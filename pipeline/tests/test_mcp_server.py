"""Test MCP server: phân quyền tool theo role + guard chống leo scope_team."""
import importlib

import pytest

import mcp_server as m


def test_staff_role_excludes_manager_tools():
    names = set(m.registered_tool_names("staff"))
    assert "search_knowledge_base" in names
    assert "get_team_priority_tasks" in names
    assert "get_feedback_summary" not in names  # tool cấp điều hành
    assert "get_hot_areas" not in names
    assert "get_sla_tickets" not in names


def test_manager_role_adds_reporting_tools():
    names = set(m.registered_tool_names("manager"))
    assert {"get_feedback_summary", "get_hot_areas", "get_sla_tickets"} <= names


@pytest.mark.parametrize("role", ["pending", "guest", None, "__hacker__"])
def test_pending_or_unknown_role_has_no_tools(role):
    """Decision 0017: the guest tool tier is gone; Pending means no access at all."""
    assert m.registered_tool_names(role) == []


def test_submit_feedback_is_no_longer_an_mcp_tool():
    """It was the guest-only tool. Customers report through the Customer web now."""
    for role in ("admin", "manager", "staff", "pending"):
        assert "submit_feedback" not in m.registered_tool_names(role)
    assert "submit_feedback" not in m.make_tool_handlers(lambda: ("admin", None, "u1"))


def test_pending_tool_call_is_refused_at_execution(monkeypatch):
    called = []
    monkeypatch.setattr(m, "execute_tool", lambda *a, **k: called.append(a) or "leaked")
    out = m.call_tool("pending", None, "get_hot_areas", {}, user_id="u1")
    assert "không có quyền" in out
    assert called == []


def test_admin_role_has_all_ops_tools():
    names = set(m.registered_tool_names("admin"))
    assert {
        "get_feedback_summary", "get_hot_areas", "get_sla_tickets",
        "get_team_priority_tasks", "search_knowledge_base",
    } <= names


def test_scope_team_cannot_be_overridden_by_args(monkeypatch):
    """Client cố truyền team_name khác trong args — server vẫn ép về phòng của mình."""
    captured = {}

    def fake_execute(name, args, scope_team=None, sources_out=None):
        captured["scope_team"] = scope_team
        captured["args"] = args
        return "ok"

    monkeypatch.setattr(m, "execute_tool", fake_execute)
    m.call_tool(role="staff", scope_team="CSKH",
                name="get_team_priority_tasks", args={"team_name": "Safety"})
    assert captured["scope_team"] == "CSKH"  # bị ép về phòng server, không nghe args


def test_admin_scope_is_system_wide(monkeypatch):
    captured = {}

    def fake_execute(name, args, scope_team=None, sources_out=None):
        captured["scope_team"] = scope_team
        return "ok"

    monkeypatch.setattr(m, "execute_tool", fake_execute)
    m.call_tool(role="admin", scope_team="CSKH", name="get_hot_areas", args={})
    assert captured["scope_team"] is None  # admin = toàn hệ thống, bỏ qua scope


def test_handlers_pass_identity_to_call_tool(monkeypatch):
    captured = {}

    def fake_execute(name, args, scope_team=None, sources_out=None):
        captured["name"] = name
        captured["scope_team"] = scope_team
        return "ok"

    monkeypatch.setattr(m, "execute_tool", fake_execute)
    handlers = m.make_tool_handlers(lambda: ("staff", "CSKH", "u1"))
    handlers["search_knowledge_base"](query="quy trình")
    assert captured == {"name": "search_knowledge_base", "scope_team": "CSKH"}


def test_build_server_ops_requires_scope(monkeypatch):
    monkeypatch.setenv("MCP_ROLE", "staff")
    monkeypatch.delenv("MCP_SCOPE_TEAM", raising=False)
    importlib.reload(m)
    with pytest.raises(SystemExit):
        m.build_server()
    importlib.reload(m)  # trả module về trạng thái sạch cho test khác


def test_build_server_defaults_to_no_tools(monkeypatch):
    """No MCP_ROLE means Pending, which means an empty tool list, not a guest tier."""
    monkeypatch.delenv("MCP_ROLE", raising=False)
    importlib.reload(m)
    assert m._resolve_identity() == ("pending", None)
    importlib.reload(m)


def test_build_server_admin_registers_tools(monkeypatch):
    monkeypatch.setenv("MCP_ROLE", "admin")
    monkeypatch.setenv("MCP_SCOPE_TEAM", "")
    importlib.reload(m)
    srv = m.build_server()
    assert srv is not None
    importlib.reload(m)
