"""HTTP MCP server (streamable-http) + auth token→role/scope — multi-user, deploy được.

Mỗi request mang `Authorization: Bearer <token>`. Middleware ASGI tra `mcp_tokens`
→ identity (role, scope_team), set ContextVar cho request đó; tool handler đọc identity
này. scope_team lấy từ token, KHÔNG từ args → client không leo quyền. Role được kiểm ở
`call_tool` (đăng ký sẵn mọi tool nhưng chặn theo role mỗi request).

Stateless (`stateless_http=True`) để scale ngang và để ContextVar propagate trong cùng
task xử lý request.

Chạy: `PORT=8000 .venv/bin/python mcp_http.py` → client nối `http://host:PORT/mcp`.
"""
import contextvars
import os

from mcp.server.fastmcp import FastMCP

from mcp_auth import verify_token
from mcp_server import make_tool_handlers, _description_for

_identity: contextvars.ContextVar = contextvars.ContextVar(
    "mcp_identity", default=(None, None)
)

_ALL_TOOLS = [
    "get_feedback_summary", "get_hot_areas", "get_sla_tickets",
    "get_team_priority_tasks", "search_knowledge_base", "submit_feedback",
]


def _current_identity():
    return _identity.get()


class AuthMiddleware:
    """ASGI middleware thuần (không dùng BaseHTTPMiddleware để ContextVar propagate)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # lifespan / websocket → passthrough (để session manager của MCP khởi động)
            return await self.app(scope, receive, send)

        if scope.get("path", "") == "/health":
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
            await send({"type": "http.response.body", "body": b"ok"})
            return

        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode()
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        ident = verify_token(token) if token else None
        if not ident:
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8"),
                                    (b"www-authenticate", b"Bearer")]})
            await send({"type": "http.response.body", "body": b"Unauthorized"})
            return

        tok = _identity.set((ident["role"], ident["scope_team"]))
        try:
            await self.app(scope, receive, send)
        finally:
            _identity.reset(tok)


def build_app():
    server = FastMCP("xanhsm-quality", stateless_http=True, json_response=True)
    handlers = make_tool_handlers(_current_identity)
    # Đăng ký sẵn mọi tool; quyền theo role được chặn ở call_tool mỗi request.
    for name in _ALL_TOOLS:
        server.add_tool(handlers[name], name=name, description=_description_for(name))
    return AuthMiddleware(server.streamable_http_app())


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(build_app(), host="0.0.0.0", port=port)
