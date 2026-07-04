from collections import Counter
from datetime import datetime, timedelta, timezone

from supabase import Client, create_client

from agents.router_agent import route_ticket
from agents.ticket_agent import create_or_update_ticket
from clean import mask_pii
from db_utils import fetch_paginated
from departments import alert_department
from env_config import get_settings, get_supabase_config, has_supabase_admin_key
from llm_agent import analyze_spike
from webhook_notifier import send_alert_webhook

SUPABASE_URL, SUPABASE_KEY = get_supabase_config()
_settings = get_settings()

# P5 tạo ngay; P4 cần một cụm nhỏ; mức thấp chỉ tạo khi có volume spike.
CRITICAL_THRESHOLD = _settings.ticket_critical_threshold
HIGH_RISK_THRESHOLD = _settings.ticket_high_risk_threshold
VOLUME_SPIKE_THRESHOLD = _settings.ticket_volume_spike_threshold
OPPORTUNITY_SPIKE_THRESHOLD = _settings.ticket_opportunity_spike_threshold
ALERT_COOLDOWN_MINUTES = _settings.ticket_alert_cooldown_minutes


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Thiếu cấu hình SUPABASE_URL và SUPABASE key trong .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _severity_number(row: dict) -> int:
    try:
        overall_risk = int(row.get("overall_risk"))
        if 1 <= overall_risk <= 5:
            return overall_risk
    except (TypeError, ValueError):
        pass
    try:
        return int(str(row.get("severity", "0")).upper().lstrip("P"))
    except (TypeError, ValueError):
        return 0

def _group_threshold(group: dict) -> int | None:
    max_severity = group["max_severity"]
    if max_severity >= 5:
        return CRITICAL_THRESHOLD
    if max_severity >= 4:
        return HIGH_RISK_THRESHOLD
    if group["ticket_type"] == "opportunity":
        return OPPORTUNITY_SPIKE_THRESHOLD
    if group["sentiments"].get("negative", 0) > 0:
        return VOLUME_SPIKE_THRESHOLD
    return None


def _is_duplicate(recent_alerts: list[dict], *, area: str, team: str, topic: str) -> bool:
    for alert in recent_alerts:
        if str(alert.get("area") or "Unknown") != area:
            continue
        if alert_department(alert) != team:
            continue
        existing_topic = str(alert.get("topic") or "").strip()
        if not existing_topic or existing_topic == topic:
            return True
    return False


def _select_candidates(candidates: list[dict], recent_alerts: list[dict], limit: int) -> list[dict]:
    """Select the highest-risk group per department before filling remaining slots."""
    viable = [
        group
        for group in candidates
        if not _is_duplicate(
            recent_alerts,
            area=group["area"],
            team=group["team"],
            topic=group["topic"],
        )
    ]
    selected: list[dict] = []
    selected_ids: set[int] = set()
    selected_teams: set[str] = set()

    # candidates đã sort theo severity/volume, nên item đầu mỗi team là ưu tiên nhất.
    for group in viable:
        if group["team"] in selected_teams:
            continue
        selected.append(group)
        selected_ids.add(id(group))
        selected_teams.add(group["team"])
        if len(selected) >= limit:
            return selected

    for group in viable:
        if id(group) in selected_ids:
            continue
        selected.append(group)
        if len(selected) >= limit:
            break
    return selected


def detect_spikes(
    hours: int = 1,
    max_feedback: int = 1000,
    max_spikes: int = 3,
    texts_per_group: int = 20,
):
    """Create deterministic tickets from risk or volume spikes.

    Feedback is grouped by area + topic + routed department. The LLM may summarize
    the group, but it never decides ownership, priority or SLA.
    """
    print("[Spike Detector] Đang quét hệ thống để tìm kiếm sự cố bùng nổ...")
    if not has_supabase_admin_key():
        return {
            "spikes_detected": 0,
            "warning": "Missing SUPABASE_SERVICE_ROLE_KEY in root .env. Spike detection may only see public/RLS-visible rows.",
        }

    db = get_supabase()
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).isoformat()

    # Phân trang: PostgREST cap 1000/response nên .limit(max_feedback>1000) sẽ quét thiếu data.
    data = fetch_paginated(
        lambda: db.table("feedback")
        .select("id,text,area,severity,overall_risk,topic,sentiment")
        .gte("created_at", since)
        .order("created_at", desc=True),
        cap=max_feedback,
    )
    if not data:
        return {"spikes_detected": 0, "records_scanned": 0, "alerts_created": 0}

    groups: dict[tuple[str, str, str, str], dict] = {}
    for row in data:
        area = str(row.get("area") or "Unknown")
        topic = str(row.get("topic") or "Other")
        sentiment = str(row.get("sentiment") or "neutral").lower()
        severity = _severity_number(row)
        effective_severity = f"P{severity}" if severity else row.get("severity", "P3")
        route = route_ticket(topic, effective_severity, sentiment, log_run=False)
        team = route["team"]
        ticket_type = "opportunity" if team == "Sản phẩm" and sentiment == "positive" else "incident"
        key = (area, topic, team, ticket_type)
        group = groups.setdefault(
            key,
            {
                "area": area,
                "topic": topic,
                "team": team,
                "ticket_type": ticket_type,
                "rows": [],
                "texts": [],
                "sentiments": Counter(),
                "max_severity": 0,
            },
        )
        group["rows"].append(row)
        group["sentiments"][sentiment] += 1
        group["max_severity"] = max(group["max_severity"], severity)
        if len(group["texts"]) < texts_per_group:
            group["texts"].append(mask_pii(str(row.get("text") or "")))

    candidates = []
    for group in groups.values():
        threshold = _group_threshold(group)
        if threshold is not None and len(group["rows"]) >= threshold:
            group["threshold"] = threshold
            candidates.append(group)
    candidates.sort(
        key=lambda group: (group["max_severity"], len(group["rows"]) / group["threshold"]),
        reverse=True,
    )

    cooldown_since = (now - timedelta(minutes=ALERT_COOLDOWN_MINUTES)).isoformat()
    try:
        recent_alerts = (
            db.table("alerts")
            .select("*")
            .gte("created_at", cooldown_since)
            .execute()
            .data
            or []
        )
    except Exception:
        recent_alerts = []

    selected = _select_candidates(candidates, recent_alerts, max_spikes)

    profiles_res = db.table("profiles").select("id").limit(1).execute()
    user_id = profiles_res.data[0]["id"] if profiles_res.data else None
    alerts_created = 0

    for group in selected:
        area = group["area"]
        route = route_ticket(
            group["topic"],
            f"P{group['max_severity']}",
            group["sentiments"].most_common(1)[0][0],
            log_run=False,
        )
        analysis = analyze_spike(area, group["texts"])
        description = (
            analysis.get("description", "Không có mô tả chi tiết")
            + f"\n\n**Action Plan:** {analysis.get('action', '')}"
            + f"\n**Assigned Team:** {route['team']}"
            + f"\n**Priority:** {route.get('priority') or 'P3'}"
            + f"\n**Routing Note:** {route.get('description') or 'Không có ghi chú'}"
        )
        severity = f"P{max(1, group['max_severity'])}"
        result = create_or_update_ticket(
            area=area,
            title=analysis.get("title", f"Spike {group['topic']} tại {area}"),
            description=description,
            severity=severity,
            team=route["team"],
            sla_hours=route.get("sla_hours", 24),
            user_id=user_id,
            topic=group["topic"],
            priority=route.get("priority"),
            ticket_type=group["ticket_type"],
            routing_source=route.get("routed_by", "router_agent"),
        )
        if result.get("action") == "created":
            alerts_created += 1
            if severity == "P5":
                send_alert_webhook(
                    title=analysis.get("title", f"Spike tại {area}"),
                    severity=severity,
                    area=area,
                    message=description,
                )

    return {
        "spikes_detected": len(selected),
        "candidate_spikes": len(candidates),
        "candidate_teams": dict(Counter(group["team"] for group in candidates)),
        "selected_teams": dict(Counter(group["team"] for group in selected)),
        "alerts_created": alerts_created,
        "records_scanned": len(data),
        "groups_scanned": len(groups),
        "max_feedback": max_feedback,
        "max_spikes": max_spikes,
    }


if __name__ == "__main__":
    detect_spikes()
