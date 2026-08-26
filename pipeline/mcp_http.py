"""HTTP MCP server — OAuth Resource Server (Supabase là Authorization Server).

Client kết nối KHÔNG cần token cấu hình sẵn:
  claude mcp add --transport http xanhsm <URL>/mcp
Lần đầu dùng → SDK trả 401 + WWW-Authenticate → client mở browser đăng nhập
tài khoản Supabase (xanhSM) → token OAuth (JWT Supabase) → verifier resolve
quyền LIVE từ profiles. Bearer bảng mcp_tokens vẫn nhận (máy-tới-máy).

Chạy: `PORT=8000 .venv/bin/python mcp_http.py` → MCP tại /mcp, health tại /health.
"""
import os

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_auth import SupabaseTokenVerifier
from mcp_server import make_tool_handlers, _description_for

SUPABASE_ISSUER = (os.environ.get("SUPABASE_URL", "").rstrip("/") or
                   "https://gvtoqbowulwmpzfogjwp.supabase.co") + "/auth/v1"
PUBLIC_URL = os.environ.get(
    "MCP_PUBLIC_URL", "https://mcp-http-production-ffd0.up.railway.app/mcp")

_ALL_TOOLS = [
    "get_feedback_summary", "get_hot_areas", "get_sla_tickets",
    "get_team_priority_tasks", "search_knowledge_base", "submit_feedback",
]


def _current_identity():
    at = get_access_token()
    if at is None or not getattr(at, "claims", None):
        return (None, None)
    return (at.claims.get("role"), at.claims.get("scope_team"))


def build_app():
    from mcp.server.transport_security import TransportSecuritySettings
    # Tắt DNS-rebinding protection (mặc định chỉ cho localhost → Railway host bị 421).
    # An toàn: cổng vào đã yêu cầu OAuth/bearer; protection này nhắm tấn công trình
    # duyệt vào server localhost, không áp API token-authed công khai.
    server = FastMCP(
        "xanhsm-quality",
        stateless_http=True,
        json_response=True,
        token_verifier=SupabaseTokenVerifier(),
        auth=AuthSettings(issuer_url=SUPABASE_ISSUER,
                          resource_server_url=PUBLIC_URL),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False),
    )

    @server.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    handlers = make_tool_handlers(_current_identity)
    for name in _ALL_TOOLS:
        server.add_tool(handlers[name], name=name, description=_description_for(name))
    return server.streamable_http_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(build_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
