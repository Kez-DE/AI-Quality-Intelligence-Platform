import os
from collections import Counter
from typing import Any, Optional

from ingest import get_supabase
from services.live_stream import get_live_stream_status
from agents.router_agent import route_ticket
from agents.analyst_agent import DEPARTMENT_PERSONAS

AGENT_SYSTEM_PROMPT = """Bạn là AI Assistant cho Quality Operation Cockpit của xanhSM.
Nhiệm vụ: phân tích feedback, alerts, spike, vận hành khu vực, chất lượng tài xế/xe/app/thanh toán/an toàn.
Trả lời tiếng Việt, ngắn gọn, có cấu trúc, ưu tiên hành động cụ thể và mức độ ưu tiên P0/P1/P2."""

GUEST_SYSTEM_PROMPT = """You are a customer support chatbot for the AI Quality Intelligence app.
You can ONLY answer questions about how to use the app and how to submit feedback.
Do NOT provide any internal data, analytics, metrics, or system information.
If the user asks about anything else, politely redirect them to use the app's features or contact support."""


def build_agent_system_prompt(user: Any = None) -> str:
    """System prompt cho chat agent, khoác persona theo phòng ban của user.

    - admin / không gán phòng: prompt chung (nhìn toàn hệ thống).
    - ops đã gán phòng: chèn persona + ưu tiên đặc thù phòng (tái dùng
      DEPARTMENT_PERSONAS của Analyst agent để giữ một nguồn sự thật duy nhất).
    """
    dept = getattr(user, "department", None) if user is not None else None
    role = getattr(user, "role", None) if user is not None else None
    if not dept or role == "admin":
        return AGENT_SYSTEM_PROMPT

    persona = DEPARTMENT_PERSONAS.get(dept)
    if not persona:
        return AGENT_SYSTEM_PROMPT

    return (
        f"{persona['persona']}\n{persona['priorities']}\n\n"
        f"Bạn là AI Assistant của phòng {dept} trong Quality Operation Cockpit xanhSM. "
        f"CHỈ phân tích dữ liệu thuộc phòng {dept} — không tiết lộ dữ liệu phòng khác. "
        f"Trả lời tiếng Việt, ngắn gọn, có cấu trúc, ưu tiên hành động cụ thể và mức ưu tiên P0/P1/P2."
    )


def _alert_team(alert: dict) -> Optional[str]:
    """Trích phòng ban được gán của một alert từ description (alerts không có cột team)."""
    desc = alert.get("description") or ""
    if "**Assigned Team:**" in desc:
        return desc.split("**Assigned Team:**")[1].strip().split("\n")[0].strip()
    return None


def build_agent_data_context(user: Any = None) -> str:
    # Xác định phòng cần lọc: admin/không gán phòng -> None (toàn hệ thống).
    scope_team = None
    role = getattr(user, "role", None) if user is not None else None
    dept = getattr(user, "department", None) if user is not None else None
    if role != "admin" and dept:
        scope_team = dept

    try:
        db = get_supabase()
        feedback = db.table("feedback") \
            .select("area,severity,sentiment,topic,created_at") \
            .order("created_at", desc=True) \
            .limit(300) \
            .execute() \
            .data or []
        alerts = db.table("alerts") \
            .select("title,severity,area,status,description,created_at") \
            .order("created_at", desc=True) \
            .limit(60) \
            .execute() \
            .data or []
    except Exception as exc:
        return f"DATA_CONTEXT_ERROR: Không đọc được Supabase context: {str(exc)[:200]}"

    # Lọc theo phòng ban (ops): feedback qua routing table, alerts qua assigned_team.
    if scope_team:
        feedback = [
            f for f in feedback
            if route_ticket(f.get("topic", ""), f.get("severity", 3), f.get("sentiment"))["team"] == scope_team
        ]
        alerts = [a for a in alerts if _alert_team(a) == scope_team]
    alerts = alerts[:20]

    severity_counts = Counter(row.get("severity") or "unknown" for row in feedback)
    sentiment_counts = Counter(row.get("sentiment") or "unknown" for row in feedback)
    topic_counts = Counter(row.get("topic") or "unknown" for row in feedback)
    area_counts = Counter(row.get("area") or "unknown" for row in feedback)
    alert_status_counts = Counter(row.get("status") or "unknown" for row in alerts)

    def top(counter: Counter, n: int = 8) -> str:
        return ", ".join(f"{k}: {v}" for k, v in counter.most_common(n)) or "none"

    return f"""
DATA_CONTEXT:
- Phạm vi dữ liệu: {('phòng ' + scope_team) if scope_team else 'Toàn hệ thống (mọi phòng ban)'}.
- Nguồn: Supabase feedback/alerts + live stream state.
- Feedback gần nhất đã đọc: {len(feedback)} records.
- Severity: {top(severity_counts)}
- Sentiment: {top(sentiment_counts)}
- Topic top: {top(topic_counts)}
- Area top: {top(area_counts)}
- Alerts gần nhất đã đọc: {len(alerts)} records.
- Alert status: {top(alert_status_counts)}
- Live stream: {get_live_stream_status()}

Recent alerts:
{os.linesep.join([f"- [{a.get('severity')}] {a.get('status')} | {a.get('area')} | {a.get('title')}" for a in alerts[:10]]) or "- none"}
"""
