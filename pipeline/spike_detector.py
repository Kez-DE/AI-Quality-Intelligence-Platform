from collections import Counter
from datetime import datetime, timedelta, timezone

from supabase import Client, create_client

from agents.router_agent import route_ticket
from agents.ticket_agent import create_or_update_ticket
from clean import mask_pii
from db_utils import fetch_paginated
from departments import DEPARTMENTS, alert_department
from env_config import get_settings, get_supabase_config, has_supabase_admin_key
from llm_agent import analyze_spike
from webhook_notifier import send_alert_webhook

SUPABASE_URL, SUPABASE_KEY = get_supabase_config()
_settings = get_settings()

# Trần mặc định cho một lượt quét. Đặt bằng số phòng ban để mỗi phòng có cơ hội nhận
# ít nhất một ticket mỗi lượt — trần nhỏ hơn số phòng khiến phòng xếp sau luôn đói.
# Đây là NGUỒN DUY NHẤT của mặc định này (live_stream, worker, API cùng import).
DEFAULT_MAX_SPIKES = len(DEPARTMENTS)

# Alert đã đóng thì không còn là "đang xử lý", không được dùng để chặn alert mới.
ACTIVE_ALERT_STATUSES = ["open", "in_progress"]

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
    """Đã có alert đang mở cho đúng (khu vực, phòng, chủ đề) trong cửa sổ cooldown chưa.

    Chủ đề phải TRÙNG mới tính trùng. Trước đây alert thiếu topic (row legacy hoặc do
    ticket_agent ghi bằng legacy_payload) bị coi là trùng với MỌI chủ đề, nên một alert
    cũ không rõ chủ đề chặn luôn cả spike Safety mới của cùng khu vực suốt cooldown.
    """
    for alert in recent_alerts:
        if str(alert.get("area") or "Unknown") != area:
            continue
        if alert_department(alert) != team:
            continue
        if str(alert.get("topic") or "").strip() == topic:
            return True
    return False


def _select_candidates(
    candidates: list[dict], recent_alerts: list[dict], limit: int
) -> tuple[list[dict], list[dict]]:
    """Chọn nhóm rủi ro nhất của mỗi phòng trước, rồi mới lấp chỗ trống.

    Trả về ``(selected, dropped)``. ``dropped`` là các nhóm ĐỦ ngưỡng nhưng bị trần
    ``limit`` cắt — caller phải báo cáo con số này, cắt im lặng khiến vận hành tưởng
    đã quét hết trong khi phần lớn spike bị bỏ.
    """
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
            break

    if len(selected) < limit:
        for group in viable:
            if id(group) in selected_ids:
                continue
            selected.append(group)
            selected_ids.add(id(group))
            if len(selected) >= limit:
                break

    dropped = [group for group in viable if id(group) not in selected_ids]
    return selected, dropped


def detect_spikes(
    hours: int = 1,
    max_feedback: int = 1000,
    max_spikes: int = DEFAULT_MAX_SPIKES,
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
    dedup_degraded = False
    try:
        recent_alerts = (
            db.table("alerts")
            .select("area,assigned_team,topic,description,status,created_at")
            .in_("status", ACTIVE_ALERT_STATUSES)
            .gte("created_at", cooldown_since)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        # Fail-open có chủ ý (thà trùng ticket còn hơn mất cảnh báo), NHƯNG phải nói ra:
        # nuốt im biến lỗi hạ tầng thành "không có gì trùng" và gây lụt ticket không dấu vết.
        recent_alerts = []
        dedup_degraded = True
        print(f"[Spike Detector] CẢNH BÁO: không đọc được alert gần đây, dedup bị vô hiệu lượt này: {str(exc)[:200]}")

    selected, dropped = _select_candidates(candidates, recent_alerts, max_spikes)
    if dropped:
        dropped_summary = ", ".join(
            f"{g['team']}/{g['area']}/{g['topic']}" for g in dropped[:10]
        )
        print(
            f"[Spike Detector] {len(dropped)} nhóm đủ ngưỡng bị trần max_spikes={max_spikes} cắt: "
            f"{dropped_summary}{' ...' if len(dropped) > 10 else ''}"
        )

    # Alert owner must be an admin: any other profile may be a self-signed-up
    # Customer account (decision 0018), which must never own an ops alert.
    profiles_res = db.table("profiles").select("id").eq("role", "admin").limit(1).execute()
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
        # Cắt do trần max_spikes phải hiện ra ở kết quả, không được im lặng.
        "dropped_groups": len(dropped),
        "dropped_teams": dict(Counter(group["team"] for group in dropped)),
        "dedup_degraded": dedup_degraded,
        "alerts_created": alerts_created,
        "records_scanned": len(data),
        "groups_scanned": len(groups),
        "max_feedback": max_feedback,
        "max_spikes": max_spikes,
    }


if __name__ == "__main__":
    detect_spikes()
