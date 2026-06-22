import uuid
from datetime import datetime, timezone, timedelta
from collections import Counter
from agents.common import get_db
from agents.router_agent import route_ticket
from departments import alert_department
from ingest import get_supabase
from clean import mask_pii
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


def submit_feedback(content: str, topic: str = "Other", sentiment: str = "negative", user_id: str | None = None) -> str:
    """Gửi phản hồi/khiếu nại của khách hàng vào hệ thống Supabase."""
    try:
        db = get_supabase()
        safe_content = mask_pii(content[:2000])
        row = {
            "id": str(uuid.uuid4()),
            "raw_text": safe_content,
            "cleaned_text": safe_content,
            "topic": topic,
            "sentiment": sentiment,
            "severity": "P3",  # default severity cho feedback từ chat
            "source": "chat",
            "needs_review": True,
            "reviewed": False,
        }
        if user_id:
            row["user_id"] = user_id
        db.table("feedback").insert(row).execute()
        return f"✅ Phản hồi của bạn đã được ghi nhận thành công! Chúng tôi sẽ xem xét và phản hồi sớm nhất có thể."
    except Exception as e:
        return f"Lỗi khi gửi phản hồi: {str(e)[:200]}"


def search_knowledge_base(query: str, scope_team: str | None = None) -> str:
    """Tra cứu SOP/SLA/quy trình nội bộ bằng Hybrid Search (Vector + BM25 + RRF).

    scope_team != None (ops): chỉ tìm trong tài liệu của phòng đó (khớp RBAC)."""
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

# ── Tool definitions cho GUEST (giới hạn, chỉ 1 tool) ─────────────────────────
GUEST_TOOLS_DEFINITIONS = [
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
                    },
                    "topic": {
                        "type": "string",
                        "description": "Chủ đề vấn đề. Chọn một trong: Driver Behavior, Safety, Payment, App Issue, Other"
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["negative", "neutral", "positive"],
                        "description": "Cảm xúc của phản hồi"
                    }
                },
                "required": ["content"]
            }
        }
    }
]

def execute_tool(name: str, args: dict, scope_team: str | None = None) -> str:
    """Thực thi tool OPS/ADMIN. scope_team != None → ép mọi truy vấn về đúng phòng đó."""
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
        return search_knowledge_base(query=args.get("query", ""), scope_team=scope_team)
    return f"Error: Tool '{name}' not found"


def execute_guest_tool(name: str, args: dict, user_id: str | None = None) -> str:
    """Thực thi tool dành riêng cho GUEST (submit_feedback)."""
    if name == "submit_feedback":
        return submit_feedback(
            content=args.get("content", ""),
            topic=args.get("topic", "Other"),
            sentiment=args.get("sentiment", "negative"),
            user_id=user_id,
        )
    return f"Error: Guest tool '{name}' not found"
