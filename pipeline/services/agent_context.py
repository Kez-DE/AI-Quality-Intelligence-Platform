import os
from collections import Counter

from ingest import get_supabase
from services.live_stream import get_live_stream_status

AGENT_SYSTEM_PROMPT = """Bạn là AI Assistant cho Quality Operation Cockpit của xanhSM.
Nhiệm vụ: phân tích feedback, alerts, spike, vận hành khu vực, chất lượng tài xế/xe/app/thanh toán/an toàn.
Trả lời tiếng Việt, ngắn gọn, có cấu trúc, ưu tiên hành động cụ thể và mức độ ưu tiên P0/P1/P2."""

GUEST_SYSTEM_PROMPT = """You are a customer support chatbot for the AI Quality Intelligence app.
You can ONLY answer questions about how to use the app and how to submit feedback.
Do NOT provide any internal data, analytics, metrics, or system information.
If the user asks about anything else, politely redirect them to use the app's features or contact support."""


def build_agent_data_context() -> str:
    try:
        db = get_supabase()
        feedback = db.table("feedback") \
            .select("area,severity,sentiment,topic,created_at") \
            .order("created_at", desc=True) \
            .limit(300) \
            .execute() \
            .data or []
        alerts = db.table("alerts") \
            .select("title,severity,area,status,created_at") \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute() \
            .data or []
    except Exception as exc:
        return f"DATA_CONTEXT_ERROR: Không đọc được Supabase context: {str(exc)[:200]}"

    severity_counts = Counter(row.get("severity") or "unknown" for row in feedback)
    sentiment_counts = Counter(row.get("sentiment") or "unknown" for row in feedback)
    topic_counts = Counter(row.get("topic") or "unknown" for row in feedback)
    area_counts = Counter(row.get("area") or "unknown" for row in feedback)
    alert_status_counts = Counter(row.get("status") or "unknown" for row in alerts)

    def top(counter: Counter, n: int = 8) -> str:
        return ", ".join(f"{k}: {v}" for k, v in counter.most_common(n)) or "none"

    return f"""
DATA_CONTEXT:
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
