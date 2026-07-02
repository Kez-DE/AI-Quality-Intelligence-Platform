"""Test HTTP MCP: auth middleware (401 / passthrough) + ContextVar identity + role gate."""
import asyncio

import mcp_http
import mcp_server as m


async def _drive(app, headers, path="/mcp"):
    """Gọi ASGI app một lần, thu status + body."""
    scope = {"type": "http", "path": path, "method": "POST",
             "headers": [(k.encode(), v.encode()) for k, v in headers.items()]}
    sent = {}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.start":
            sent["status"] = msg["status"]
        elif msg["type"] == "http.response.body":
            sent.setdefault("body", b"")
            sent["body"] += msg.get("body", b"")

    await app(scope, receive, send)
    return sent


def test_missing_token_returns_401(monkeypatch):
    async def inner(scope, receive, send):  # phải KHÔNG được gọi
        raise AssertionError("inner app không được chạy khi thiếu token")
    mw = mcp_http.AuthMiddleware(inner)
    sent = asyncio.run(_drive(mw, {}))
    assert sent["status"] == 401


def test_invalid_token_returns_401(monkeypatch):
    monkeypatch.setattr(mcp_http, "verify_token", lambda t: None)
    async def inner(scope, receive, send):
        raise AssertionError("không được chạy")
    mw = mcp_http.AuthMiddleware(inner)
    sent = asyncio.run(_drive(mw, {"authorization": "Bearer bad"}))
    assert sent["status"] == 401


def test_valid_token_sets_identity_and_delegates(monkeypatch):
    monkeypatch.setattr(mcp_http, "verify_token",
                        lambda t: {"role": "manager", "scope_team": "CSKH"})
    seen = {}

    async def inner(scope, receive, send):
        seen["identity"] = mcp_http._current_identity()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = mcp_http.AuthMiddleware(inner)
    sent = asyncio.run(_drive(mw, {"authorization": "Bearer good"}))
    assert sent["status"] == 200
    assert seen["identity"] == ("manager", "CSKH")
    # sau request, ContextVar phải reset về default
    assert mcp_http._current_identity() == (None, None)


def test_health_bypasses_auth():
    async def inner(scope, receive, send):
        raise AssertionError("health không đi vào inner app")
    mw = mcp_http.AuthMiddleware(inner)
    sent = asyncio.run(_drive(mw, {}, path="/health"))
    assert sent["status"] == 200 and sent["body"] == b"ok"


def test_role_gate_blocks_disallowed_tool():
    # staff không được dùng get_feedback_summary → call_tool trả thông báo chặn
    out = m.call_tool("staff", "CSKH", "get_feedback_summary", {"days": 7})
    assert "không có quyền" in out


def test_unknown_role_has_no_tools():
    assert m.registered_tool_names(None) == []
    assert m.registered_tool_names("__hacker__") == []
