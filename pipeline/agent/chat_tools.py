import uuid
from datetime import datetime, timezone, timedelta
from collections import Counter
from agents.common import get_db
from agents.router_agent import route_ticket
from departments import alert_department
from ingest import get_supabase
from .knowledge_base import search_knowledge, format_for_prompt
from .rag_engine import _vector_search, _hybrid_merge, embedder


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
                if route_ticket(
                    f.get("topic", ""), f.get("severity", 3), f.get("sentiment"), log_run=False
                )["team"] == scope_team
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
            .select("*") \
            .in_("status", ["open", "in_progress"]) \
            .order("created_at", desc=False) \
            .limit(40) \
            .execute().data or []

        # Lọc theo phòng ban nếu là ops (qua assigned_team trong description)
        if scope_team:
            alerts = [a for a in alerts if alert_department(a) == scope_team]
        alerts = alerts[:10]

        if not alerts:
            scope_txt = f" của phòng {scope_team}" if scope_team else ""
            return f"Tuyệt vời, không có ticket nào{scope_txt} đang tồn đọng hoặc vi phạm SLA."

        result = ["Danh sách ticket tồn đọng lâu nhất (Nguy cơ SLA):"]
        for a in alerts:
            team = alert_department(a) or "—"
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


def submit_feedback(content: str, user_id: str | None = None) -> str:
    """Gửi phản hồi từ trợ lý công khai (public_only của staff) vào `feedback`.

    Nhãn (topic/sentiment/severity) do classifier gán qua cùng đường với public
    intake — không để model tự chọn nhãn hay mặc định P3 (decision 0018).
    `user_id` bắt buộc: bản ghi không có public_ref thì phải có chủ
    (feedback_identity_chk), nên từ chối rõ ràng thay vì để tầng dưới ném lỗi.
    """
    if not user_id:
        return "Không gửi được phản hồi: phiên đăng nhập chưa xác định người gửi."
    try:
        from public_intake import MAX_PUBLIC_TEXT, classified_fields

        db = get_supabase()
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "source": "chat",
            "reviewed": False,
            **classified_fields(content[:MAX_PUBLIC_TEXT]),
            # Unchanged staff flow: every landing-assistant report goes to the Review Queue.
            "needs_review": True,
        }
        db.table("feedback").insert(row).execute()
        return f"✅ Phản hồi của bạn đã được ghi nhận thành công! Chúng tôi sẽ xem xét và phản hồi sớm nhất có thể."
    except Exception as e:
        print(f"[chat_tools] submit_feedback failed: {type(e).__name__}")
        return "Không gửi được phản hồi, vui lòng thử lại."


def search_knowledge_base(query: str, scope_team: str | None = None, sources_out: list | None = None) -> str:
    """Tra cứu SOP/SLA/quy trình nội bộ bằng Hybrid Search (Vector + BM25 + RRF).

    scope_team != None (ops): chỉ tìm trong tài liệu của phòng đó (khớp RBAC).
    sources_out != None: ghi thêm nguồn có cấu trúc để client hiện trích dẫn [Nguồn N] bấm được."""
    try:
        query_emb = embedder.embed_query(query)
        vector_results = _vector_search(query_emb, scope_team, top_k=6)
        keyword_results = search_knowledge(query, department=scope_team, top_k=6)
        merged = _hybrid_merge(vector_results, keyword_results, top_k=3)

        if not merged:
            return "Không tìm thấy tài liệu nội bộ nào liên quan đến câu hỏi này."

        blocks = ["Tài liệu nội bộ liên quan (trích dẫn nguồn khi trả lời):"]
        for i, r in enumerate(merged, 1):
            dept = r.get("department") or "chung"
            blocks.append(
                f"\n[Nguồn {i}] {r['document_title']} › {r['heading']} (phòng: {dept})\n{r['content']}"
            )
            if sources_out is not None:
                sources_out.append({
                    "index": i,
                    "title": r.get("document_title") or "Tài liệu nội bộ",
                    "heading": r.get("heading") or "",
                    "department": dept,
                    "content": r.get("content") or "",
                })
        return "\n".join(blocks)
    except Exception as e:
        # Fallback về BM25 nếu Hybrid lỗi (vd: Cohere API down)
        try:
            results = search_knowledge(query, department=scope_team, top_k=3)
            return format_for_prompt(results)
        except Exception:
            return f"Lỗi tra cứu knowledge base: {str(e)[:200]}"


def get_feedback_summary(days: int = 7, scope_team: str | None = None) -> str:
    """Tổng hợp feedback theo topic/severity/area trong N ngày gần nhất dưới dạng bảng Markdown."""
    try:
        db = get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        feedback = (
            db.table("feedback")
            .select("topic,severity,sentiment,area,created_at")
            .gte("created_at", cutoff)
            .execute()
            .data or []
        )

        if scope_team:
            feedback = [
                f for f in feedback
                if route_ticket(
                    f.get("topic", ""), f.get("severity", 3), f.get("sentiment"), log_run=False
                )["team"] == scope_team
            ]

        if not feedback:
            scope_txt = f" của phòng {scope_team}" if scope_team else ""
            return f"Không có feedback nào{scope_txt} trong {days} ngày qua."

        topic_counts = Counter(f.get("topic") or "Unknown" for f in feedback)
        severity_counts = Counter(f.get("severity") or "Unknown" for f in feedback)
        sentiment_counts = Counter(f.get("sentiment") or "Unknown" for f in feedback)
        area_counts = Counter(f.get("area") or "Unknown" for f in feedback)

        scope_txt = f" (Phòng {scope_team})" if scope_team else " (Toàn hệ thống)"
        lines = [
            f"## Tổng hợp Feedback {days} ngày qua{scope_txt}",
            f"**Tổng số:** {len(feedback)} feedback\n",
            "### Theo Chủ đề (Topic)",
            "| Chủ đề | Số lượng |",
            "|---|---|",
        ]
        for topic, cnt in topic_counts.most_common(8):
            lines.append(f"| {topic} | {cnt} |")

        lines += [
            "\n### Theo Mức độ (Severity)",
            "| Severity | Số lượng |",
            "|---|---|",
        ]
        for sev in ["P5", "P4", "P3", "P2", "P1"]:
            cnt = severity_counts.get(sev, 0)
            if cnt:
                lines.append(f"| {sev} | {cnt} |")

        lines += [
            "\n### Cảm xúc (Sentiment)",
            f"- 😡 Tiêu cực: {sentiment_counts.get('negative', 0)}",
            f"- 😐 Trung tính: {sentiment_counts.get('neutral', 0)}",
            f"- 😊 Tích cực: {sentiment_counts.get('positive', 0)}",
            "\n### Top 5 Khu vực nóng",
            "| Khu vực | Số feedback |",
            "|---|---|",
        ]
        for area, cnt in area_counts.most_common(5):
            lines.append(f"| {area} | {cnt} |")

        return "\n".join(lines)
    except Exception as e:
        return f"Lỗi khi tổng hợp feedback: {str(e)[:200]}"

# ── Tool definitions cho OPS / ADMIN ──────────────────────────────────────────
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_feedback_summary",
            "description": "Tổng hợp feedback theo topic/severity/area trong N ngày qua — dùng khi user hỏi 'tổng hợp vấn đề nổi cộm', 'xu hướng tuần này', 'các vấn đề chính trong N ngày qua'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Số ngày gần nhất để tổng hợp (mặc định 7)"
                    }
                }
            }
        }
    },
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
            "description": "Tra cứu quy trình/SOP/SLA nội bộ (tai nạn, gian lận cước, thái độ tài xế, lỗi thanh toán, bồi thường...) để trả lời ĐÚNG theo tài liệu và TRÍCH DẪN nguồn. Dùng khi user hỏi 'xử lý thế nào', 'quy trình', 'chính sách', 'SLA bao lâu'.",
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

# ── Tool definitions cho TẦNG CÔNG KHAI (public_only, chỉ 1 tool) ──────────────
PUBLIC_TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "submit_feedback",
            "description": "Gửi phản hồi hoặc khiếu nại của khách hàng vào hệ thống. Dùng khi khách hàng nói muốn 'gửi phản hồi', 'khiếu nại', 'báo cáo sự cố', 'phàn nàn', hoặc yêu cầu ghi nhận ý kiến.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Nội dung phản hồi/khiếu nại của khách hàng"
                    }
                },
                "required": ["content"]
            }
        }
    }
]

def execute_tool(name: str, args: dict, scope_team: str | None = None, sources_out: list | None = None) -> str:
    """Thực thi tool OPS/ADMIN. scope_team != None → ép mọi truy vấn về đúng phòng đó.
    sources_out: thu thập nguồn có cấu trúc từ search_knowledge_base (cho trích dẫn click được)."""
    if name == "get_feedback_summary":
        return get_feedback_summary(days=args.get("days", 7), scope_team=scope_team)
    elif name == "get_hot_areas":
        return get_hot_areas(hours=args.get("hours", 24), limit=args.get("limit", 5), scope_team=scope_team)
    elif name == "get_sla_tickets":
        return get_sla_tickets(scope_team=scope_team)
    elif name == "get_team_priority_tasks":
        # ops: luôn ép về phòng của mình; admin (scope_team=None): tôn trọng tham số.
        team = scope_team or args.get("team_name", "")
        return get_team_priority_tasks(team_name=team)
    elif name == "search_knowledge_base":
        return search_knowledge_base(query=args.get("query", ""), scope_team=scope_team, sources_out=sources_out)
    return f"Error: Tool '{name}' not found"


def execute_public_tool(name: str, args: dict, user_id: str | None = None) -> str:
    """Thực thi tool của tầng công khai (submit_feedback)."""
    if name == "submit_feedback":
        # Labels come from the classifier; any topic/sentiment the model sends is ignored.
        return submit_feedback(content=str(args.get("content", "")), user_id=user_id)
    return f"Error: Public tool '{name}' not found"


# ── Phân tầng tool theo VAI TRÒ (role) ────────────────────────────────────────
# Lưu ý: scope_team (phòng ban) đã được ép riêng trong execute_tool, nên các tool
# dưới đây luôn bị giới hạn về đúng phòng của ops (admin = toàn hệ thống). Phần này
# giới hạn THÊM theo vai trò — quyết định mỗi role được "nhìn thấy" những tool nào.
#   • staff   : chỉ tra cứu SOP/quy trình (cách làm) + task ưu tiên của phòng mình
#               (hướng giải quyết) — không xem tổng hợp/phân tích cấp điều hành.
#   • manager : thêm tổng hợp feedback, khu vực nóng, ticket sắp vi phạm SLA (báo cáo),
#               vẫn bị scope_team giới hạn trong phòng mình — không "full" như admin.
#   • admin   : toàn bộ tool, toàn hệ thống.
_TOOL_BY_NAME = {t["function"]["name"]: t for t in TOOLS_DEFINITIONS}
_STAFF_TOOL_NAMES = ["search_knowledge_base", "get_team_priority_tasks"]
_MANAGER_TOOL_NAMES = _STAFF_TOOL_NAMES + [
    "get_feedback_summary",
    "get_hot_areas",
    "get_sla_tickets",
]


def tools_for_role(role: str | None) -> list:
    """Bộ tool OPS theo vai trò. scope_team (phòng ban) vẫn ép riêng ở execute_tool.

    Mặc định FAIL-CLOSED: vai trò không nhận ra thì KHÔNG có tool vận hành nào.
    Trước đây nhánh mặc định trả về toàn bộ tool, nghĩa là một vai trò mới thêm
    vào hệ thống sẽ im lặng nhận quyền admin — đúng mẫu thất bại trong im lặng.
    """
    if role == "admin":
        return TOOLS_DEFINITIONS
    if role == "manager":
        return [_TOOL_BY_NAME[n] for n in _MANAGER_TOOL_NAMES if n in _TOOL_BY_NAME]
    if role == "staff":
        return [_TOOL_BY_NAME[n] for n in _STAFF_TOOL_NAMES if n in _TOOL_BY_NAME]
    return []
