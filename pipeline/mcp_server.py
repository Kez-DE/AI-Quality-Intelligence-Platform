"""MCP server (stdio) expose các tool nghiệp vụ của platform ra ngoài.

Danh tính CỐ ĐỊNH phía server qua env — client KHÔNG truyền được:
  MCP_ROLE       admin | manager | staff | guest   (mặc định guest)
  MCP_SCOPE_TEAM tên phòng ban; rỗng = toàn hệ thống (chỉ hợp lệ khi admin)

Đây là adapter mỏng: KHÔNG sửa agent/chat_tools.py, chỉ gọi vào. Ranh giới bảo
mật: scope_team luôn lấy từ config server, không bao giờ từ tham số tool, nên MCP
client không leo được ra khỏi phòng ban của mình. MCP_ROLE quyết định tool nào
tồn tại.

Chạy: `MCP_ROLE=admin .venv/bin/python mcp_server.py`
"""
import os

from agent.chat_tools import (
    tools_for_role,
    execute_tool,
    execute_guest_tool,
    GUEST_TOOLS_DEFINITIONS,
)


def registered_tool_names(role: str | None) -> list[str]:
    """Tên các tool role này được thấy. guest = chỉ submit_feedback."""
    if role == "guest":
        return [t["function"]["name"] for t in GUEST_TOOLS_DEFINITIONS]
    return [t["function"]["name"] for t in tools_for_role(role)]


def call_tool(role: str | None, scope_team: str | None, name: str, args: dict) -> str:
    """Route một tool call. scope_team LUÔN từ config server, không bao giờ từ args."""
    if role == "guest":
        return execute_guest_tool(name, args, user_id=None)
    # admin: scope_team=None (toàn hệ thống). ops (staff/manager): ép về phòng của server.
    effective_scope = None if role == "admin" else scope_team
    return execute_tool(name, args, scope_team=effective_scope)


def _description_for(name: str, role: str | None) -> str:
    defs = GUEST_TOOLS_DEFINITIONS if role == "guest" else tools_for_role(role)
    for t in defs:
        if t["function"]["name"] == name:
            return t["function"]["description"]
    return name


def _resolve_identity() -> tuple[str, str | None]:
    role = (os.environ.get("MCP_ROLE") or "guest").strip().lower()
    scope_team = (os.environ.get("MCP_SCOPE_TEAM") or "").strip() or None
    if role in ("staff", "manager") and scope_team is None:
        raise SystemExit("MCP_SCOPE_TEAM bắt buộc khi MCP_ROLE là staff/manager")
    return role, scope_team


def build_server():
    """Dựng FastMCP server, đăng ký đúng tập tool theo role. Import mcp ở đây để
    phần lõi (registered_tool_names/call_tool) test được mà không cần mcp SDK."""
    from mcp.server.fastmcp import FastMCP

    role, scope_team = _resolve_identity()
    server = FastMCP("xanhsm-quality")

    # Wrapper có signature rõ ràng để FastMCP sinh input schema đúng cho client.
    # Mỗi wrapper đóng kín role/scope_team; args tool KHÔNG chứa scope_team.
    def get_feedback_summary(days: int = 7) -> str:
        return call_tool(role, scope_team, "get_feedback_summary", {"days": days})

    def get_hot_areas(hours: int = 24, limit: int = 5) -> str:
        return call_tool(role, scope_team, "get_hot_areas", {"hours": hours, "limit": limit})

    def get_sla_tickets() -> str:
        return call_tool(role, scope_team, "get_sla_tickets", {})

    def get_team_priority_tasks(team_name: str) -> str:
        return call_tool(role, scope_team, "get_team_priority_tasks", {"team_name": team_name})

    def search_knowledge_base(query: str) -> str:
        return call_tool(role, scope_team, "search_knowledge_base", {"query": query})

    def submit_feedback(content: str, topic: str = "Other", sentiment: str = "negative") -> str:
        return call_tool(role, scope_team, "submit_feedback",
                         {"content": content, "topic": topic, "sentiment": sentiment})

    handlers = {
        "get_feedback_summary": get_feedback_summary,
        "get_hot_areas": get_hot_areas,
        "get_sla_tickets": get_sla_tickets,
        "get_team_priority_tasks": get_team_priority_tasks,
        "search_knowledge_base": search_knowledge_base,
        "submit_feedback": submit_feedback,
    }

    for name in registered_tool_names(role):
        fn = handlers.get(name)
        if fn is None:
            continue
        server.add_tool(fn, name=name, description=_description_for(name, role))
    return server


if __name__ == "__main__":
    build_server().run()  # stdio transport mặc định
