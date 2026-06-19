from datetime import datetime, timezone, timedelta
from collections import Counter
from agents.common import get_db
from agents.router_agent import route_ticket
from .knowledge_base import search_knowledge, format_for_prompt


def _alert_team(alert: dict) -> str | None:
    """Trích phòng ban của alert từ description (alerts không có cột team)."""
    desc = alert.get("description") or ""
    if "**Assigned Team:**" in desc:
        return desc.split("**Assigned Team:**")[1].strip().split("\n")[0].strip()
    return None


def get_hot_areas(hours: int = 24, limit: int = 5, scope_team: str | None = None) -> str:
    """Lấy danh sách các khu vực đang có nhiều feedback tiêu cực hoặc alert nhất."""
    try:
        db = get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # Lấy feedback
        feedback = db.table("feedback") \
            .select("area,severity,topic,sentiment") \
            .gte("created_at", cutoff) \
            .in_("sentiment", ["negative"]) \
            .execute().data or []

        # Lọc theo phòng ban nếu là ops (qua routing table)
        if scope_team:
            feedback = [
                f for f in feedback
                if route_ticket(f.get("topic", ""), f.get("severity", 3), f.get("sentiment"))["team"] == scope_team
            ]

        # Đếm theo area
        area_counts = Counter(f.get("area") for f in feedback if f.get("area"))
        if not area_counts:
            scope_txt = f" cho phòng {scope_team}" if scope_team else ""
            return f"Không có khu vực nào có feedback tiêu cực trong {hours} giờ qua{scope_txt}."

        top_areas = area_counts.most_common(limit)
        result = [f"Top {limit} khu vực nóng trong {hours}h qua{(' — phòng ' + scope_team) if scope_team else ''}:"]
        for area, count in top_areas:
            result.append(f"- {area}: {count} feedback tiêu cực")
        return "\n".join(result)
    except Exception as e:
        return f"Lỗi truy xuất dữ liệu: {str(e)}"

def get_sla_tickets(scope_team: str | None = None) -> str:
    """Lấy danh sách các ticket/alert đang mở và sắp/đã quá hạn SLA."""
    try:
        db = get_db()
        alerts = db.table("alerts") \
            .select("id,title,area,status,severity,description,created_at") \
            .in_("status", ["open", "in_progress"]) \
            .order("created_at", desc=False) \
            .limit(40) \
            .execute().data or []

        # Lọc theo phòng ban nếu là ops (qua assigned_team trong description)
        if scope_team:
            alerts = [a for a in alerts if _alert_team(a) == scope_team]
        alerts = alerts[:10]

        if not alerts:
            scope_txt = f" của phòng {scope_team}" if scope_team else ""
            return f"Tuyệt vời, không có ticket nào{scope_txt} đang tồn đọng hoặc vi phạm SLA."

        result = ["Danh sách ticket tồn đọng lâu nhất (Nguy cơ SLA):"]
        for a in alerts:
            team = _alert_team(a) or "—"
            result.append(f"- [ID: {a.get('id')}] [{a.get('severity')}] {team} | {a.get('area')}: {a.get('title')}")
        return "\n".join(result)
    except Exception as e:
        return f"Lỗi truy xuất dữ liệu: {str(e)}"

def get_team_priority_tasks(team_name: str) -> str:
    """Lấy danh sách các task/ticket đang cần ưu tiên xử lý của một phòng ban cụ thể."""
    try:
        db = get_db()
        tasks = db.table("tasks") \
            .select("id,title,priority,status,area,due_at") \
            .eq("assigned_team", team_name) \
            .in_("status", ["open", "in_progress"]) \
            .order("priority", desc=True) \
            .limit(5) \
            .execute().data or []
            
        if not tasks:
            return f"Phòng ban {team_name} hiện không có task nào đang mở."
            
        result = [f"Danh sách task ưu tiên của {team_name}:"]
        for t in tasks:
            due = t.get("due_at") or "None"
            result.append(f"- [ID: {t.get('id')}] [{t.get('priority')}] {t.get('area')}: {t.get('title')} (Hạn: {due})")
        return "\n".join(result)
    except Exception as e:
        return f"Lỗi truy xuất dữ liệu: {str(e)}"


def search_knowledge_base(query: str, scope_team: str | None = None) -> str:
    """Tra cứu SOP/SLA/quy trình nội bộ (RAG) để trả lời có trích dẫn, không bịa.

    scope_team != None (ops): chỉ tìm trong tài liệu của phòng đó (khớp RBAC)."""
    try:
        results = search_knowledge(query, department=scope_team, top_k=3)
        return format_for_prompt(results)
    except Exception as e:
        return f"Lỗi tra cứu knowledge base: {str(e)}"

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_hot_areas",
            "description": "Lấy danh sách các khu vực đang có nhiều feedback tiêu cực nhất để xem khu vực nào đang 'nóng'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Số giờ gần nhất để phân tích (mặc định 24)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng khu vực trả về (mặc định 5)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sla_tickets",
            "description": "Lấy danh sách các ticket/alert đang tồn đọng (open/in_progress) lâu nhất có nguy cơ vi phạm SLA.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_priority_tasks",
            "description": "Lấy danh sách các task ưu tiên cần xử lý của một phòng ban cụ thể (vd: Safety, CSKH, IT).",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "Tên phòng ban (vd: Safety, CSKH, IT, Operations)"
                    }
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Tra cứu quy trình/SOP/SLA nội bộ (tai nạn, gian lận cước, thái độ tài xế, lỗi thanh toán, bồi thường...) để trả lời ĐÚNG theo tài liệu và TRÍCH DẪN nguồn, thay vì tự suy diễn. Dùng khi user hỏi 'xử lý thế nào', 'quy trình', 'chính sách', 'SLA bao lâu'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Câu hỏi hoặc từ khóa cần tra cứu trong tài liệu nội bộ"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def execute_tool(name: str, args: dict, scope_team: str | None = None) -> str:
    """Thực thi tool. scope_team != None (ops đã gán phòng) -> ép mọi truy vấn
    về đúng phòng đó, bỏ qua tham số team LLM tự sinh (chống rò rỉ chéo phòng)."""
    if name == "get_hot_areas":
        return get_hot_areas(hours=args.get("hours", 24), limit=args.get("limit", 5), scope_team=scope_team)
    elif name == "get_sla_tickets":
        return get_sla_tickets(scope_team=scope_team)
    elif name == "get_team_priority_tasks":
        # ops: luôn ép về phòng của mình; admin (scope_team=None): tôn trọng tham số.
        team = scope_team or args.get("team_name", "")
        return get_team_priority_tasks(team_name=team)
    elif name == "search_knowledge_base":
        return search_knowledge_base(query=args.get("query", ""), scope_team=scope_team)
    return f"Error: Tool {name} not found"
