"""Test HTTP MCP (SDK auth): identity từ auth context + role gate + app build."""
import mcp_http
import mcp_server as m


def test_identity_reads_sdk_access_token(monkeypatch):
    class _AT:
        claims = {"role": "manager", "scope_team": "CSKH", "user_id": "u1"}
    monkeypatch.setattr(mcp_http, "get_access_token", lambda: _AT())
    assert mcp_http._current_identity() == ("manager", "CSKH", "u1")


def test_identity_none_when_no_token(monkeypatch):
    monkeypatch.setattr(mcp_http, "get_access_token", lambda: None)
    assert mcp_http._current_identity() == (None, None, None)


def test_build_app_returns_asgi_app():
    app = mcp_http.build_app()
    assert callable(app)


def test_role_gate_blocks_disallowed_tool():
    out = m.call_tool("staff", "CSKH", "get_feedback_summary", {"days": 7})
    assert "không có quyền" in out


def test_unknown_role_has_no_tools():
    assert m.registered_tool_names(None) == []
    assert m.registered_tool_names("__hacker__") == []
