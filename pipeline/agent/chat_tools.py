from datetime import datetime, timezone, timedelta
from collections import Counter
from agents.common import get_db

def get_hot_areas(hours: int = 24, limit: int = 5) -> str:
    """Lấy danh sách các khu vực đang có nhiều feedback tiêu cực hoặc alert nhất."""
    try:
        db = get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        # Lấy feedback
        feedback = db.table("feedback") \
            .select("area,severity") \
            .gte("created_at", cutoff) \
            .in_("sentiment", ["negative"]) \
            .execute().data or []
            
        # Đếm theo area
        area_counts = Counter(f.get("area") for f in feedback if f.get("area"))
        if not area_counts:
            return f"Không có khu vực nào có feedback tiêu cực trong {hours} giờ qua."
            
        top_areas = area_counts.most_common(limit)
        result = [f"Top {limit} khu vực nóng trong {hours}h qua:"]
        for area, count in top_areas:
            result.append(f"- {area}: {count} feedback tiêu cực")
        return "\n".join(result)
    except Exception as e:
        return f"Lỗi truy xuất dữ liệu: {str(e)}"

def get_sla_tickets() -> str:
    """Lấy danh sách các ticket/alert đang mở và sắp/đã quá hạn SLA."""
    try:
        db = get_db()
        alerts = db.table("alerts") \
            .select("id,title,area,status,severity,created_at,assigned_team") \
            .in_("status", ["open", "in_progress"]) \
            .order("created_at", desc=False) \
            .limit(10) \
            .execute().data or []
            
        if not alerts:
            return "Tuyệt vời, không có ticket nào đang tồn đọng hoặc vi phạm SLA."
            
        result = ["Danh sách 10 ticket tồn đọng lâu nhất (Nguy cơ SLA):"]
        for a in alerts:
            result.append(f"- [ID: {a.get('id')}] [{a.get('severity')}] {a.get('assigned_team')} | {a.get('area')}: {a.get('title')}")
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
    }
]

def execute_tool(name: str, args: dict) -> str:
    if name == "get_hot_areas":
        return get_hot_areas(hours=args.get("hours", 24), limit=args.get("limit", 5))
    elif name == "get_sla_tickets":
        return get_sla_tickets()
    elif name == "get_team_priority_tasks":
        return get_team_priority_tasks(team_name=args.get("team_name", ""))
    return f"Error: Tool {name} not found"
