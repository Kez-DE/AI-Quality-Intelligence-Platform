"""Task Agent — gom alert thành Task cho phòng ban.

Hợp đồng của agent này (đọc trước khi sửa):

1. Cụm được định danh bằng ``(phòng ban, khu vực, chủ đề)``. Bỏ chủ đề ra khỏi khoá
   sẽ khiến một alert Safety P5 bị nuốt vào task "Chậm chuyến" P2 cùng khu vực.
2. Task đang ``open``/``assigned``/``in_progress`` vẫn hút được alert mới. Chỉ
   ``pending_review``/``resolved`` là ngừng hút — nếu chỉ khớp ``open`` thì ngay khi
   manager giao việc, chu kỳ sau sẽ đẻ ra task trùng.
3. Alert không bao giờ được rơi. LLM chỉ đặt tên; hỏng LLM thì dùng tiêu đề suy diễn.
4. Mức ưu tiên chỉ đi lên. Alert nặng hơn nhập vào task cũ thì nâng cấp task đó.
"""

import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from agents.common import get_db, log_agent_run
from agents.common import call_llm
from agents.router_agent import route_ticket
from departments import alert_department

# Task còn hút được alert mới. 'pending_review'/'resolved' đã khép lại nên loại ra.
ABSORBING_TASK_STATUSES = ["open", "assigned", "in_progress"]

# Alert cần được gán task. 'in_progress' cũng vào đây vì có trường hợp tiếp nhận
# ticket nhưng tạo task hụt (create_ticket_task trả None) — không quét thì mồ côi mãi.
UNASSIGNED_ALERT_STATUSES = ["open", "in_progress"]

# Trong hệ này P5 nặng nhất (Safety), P1 nhẹ nhất — cùng thang với alert.severity.
_PRIORITY_RANK = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}

_DEFAULT_SLA_HOURS = 24


def priority_rank(priority: Any) -> int:
    """Thứ hạng nghiêm trọng của mã ưu tiên. Không đọc được -> 0 (yếu nhất)."""
    return _PRIORITY_RANK.get(str(priority or "").strip().upper()[:2], 0)


def alert_priority(alert: Dict[str, Any]) -> str:
    """Mức ưu tiên của một alert: cột structured trước, Markdown legacy sau.

    Row cũ (trước migration alert_routing_fields) không có cột `priority`, mức ưu tiên
    chỉ nằm trong Markdown mô tả. Đọc cột trước để không phụ thuộc định dạng văn bản.
    """
    structured = str(alert.get("priority") or "").strip().upper()[:2]
    if structured in _PRIORITY_RANK:
        return structured

    description = str(alert.get("description") or "")
    marker = "**Priority:**"
    if marker in description:
        legacy = description.split(marker, 1)[1].strip().split("\n", 1)[0].strip().upper()[:2]
        if legacy in _PRIORITY_RANK:
            return legacy

    severity = str(alert.get("severity") or "").strip().upper()[:2]
    return severity if severity in _PRIORITY_RANK else "P2"


def cluster_sla_hours(topic: Optional[str], priority: Optional[str]) -> int:
    """SLA của cụm, lấy từ cùng bảng routing mà router_agent dùng để chia phòng.

    Task và ticket phải dùng chung một nguồn SLA, nếu không thì bảng công việc và
    bảng ticket báo quá hạn ở hai thời điểm khác nhau cho cùng một sự cố.
    """
    try:
        route = route_ticket(str(topic or "Other"), priority or "P3", log_run=False)
        return int(route.get("sla_hours") or _DEFAULT_SLA_HOURS)
    except Exception:
        return _DEFAULT_SLA_HOURS


def _due_at_iso(topic: Optional[str], priority: Optional[str]) -> str:
    hours = cluster_sla_hours(topic, priority)
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _find_absorbing_task(db, team: str, area: Any, topic: Optional[str]) -> Optional[Dict[str, Any]]:
    """Task của cụm còn hút được alert, hoặc None."""
    try:
        query = (
            db.table("tasks")
            .select("id,priority,due_at,status")
            .eq("assigned_team", team)
            .eq("area", area)
            .in_("status", ABSORBING_TASK_STATUSES)
        )
        if topic:
            query = query.eq("topic", topic)
        rows = query.limit(1).execute().data or []
        return rows[0] if rows else None
    except Exception:
        return None


def escalate_task_priority(db, task: Dict[str, Any], priority: str, topic: Optional[str]) -> bool:
    """Nâng mức ưu tiên task khi alert nặng hơn nhập vào. Trả True nếu có nâng.

    Ưu tiên chỉ đi lên: một cụm đã từng chạm P5 thì không được tụt lại khi sau đó
    chỉ còn alert nhẹ, vì task vẫn đang gánh sự cố nặng chưa đóng.
    """
    if priority_rank(priority) <= priority_rank(task.get("priority")):
        return False
    try:
        db.table("tasks").update({
            "priority": priority,
            "due_at": _due_at_iso(topic, priority),
        }).eq("id", task["id"]).execute()
        return True
    except Exception as exc:
        print(f"[TaskAgent] Không nâng được ưu tiên task {task.get('id')}: {exc}")
        return False


def find_or_create_cluster_task(
    db,
    team,
    area,
    priority,
    title,
    summary="",
    *,
    topic=None,
    source="agent",
):
    """Task của cụm (team, area, topic) — tái dùng nếu còn hút được, chưa có thì tạo.

    Không gọi LLM. Trả None khi không tạo được (caller phải xử lý, không được im lặng).
    """
    existing = _find_absorbing_task(db, team, area, topic)
    if existing:
        escalate_task_priority(db, existing, priority or "P2", topic)
        return existing["id"]

    effective_priority = priority or "P2"
    inserted = db.table("tasks").insert({
        "title": title,
        "summary": summary,
        "assigned_team": team,
        "area": area,
        "topic": topic or "Other",
        "priority": effective_priority,
        "status": "open",
        "source": source,
        "due_at": _due_at_iso(topic, effective_priority),
    }).execute()
    return inserted.data[0]["id"] if inserted.data else None


def create_ticket_task(db, team, area, priority, title, summary="", *, topic=None):
    """LUÔN tạo task MỚI gắn 1:1 với một ticket (source='ticket').

    Khác find_or_create_cluster_task: không tái dùng task cụm, vì ticket đã được một
    người tiếp nhận cụ thể và cần đường theo dõi riêng.
    """
    effective_priority = priority or "P2"
    inserted = db.table("tasks").insert({
        "title": title,
        "summary": summary,
        "assigned_team": team,
        "area": area,
        "topic": topic or "Other",
        "priority": effective_priority,
        "status": "open",
        "source": "ticket",
        "due_at": _due_at_iso(topic, effective_priority),
    }).execute()
    return inserted.data[0]["id"] if inserted.data else None


def fallback_cluster_title(team: str, area: Any, topic: Optional[str], count: int) -> Dict[str, str]:
    """Tiêu đề suy diễn từ dữ liệu cụm, dùng khi LLM hỏng hoặc bị tắt.

    Không bịa nội dung: chỉ nói đúng những gì đếm được (chủ đề, khu vực, số sự cố).
    """
    topic_label = str(topic or "sự cố").strip() or "sự cố"
    area_label = str(area or "khu vực chưa xác định").strip() or "khu vực chưa xác định"
    return {
        "title": f"{topic_label} tại {area_label}"[:120],
        "summary": (
            f"{count} cảnh báo {topic_label} chưa xử lý tại {area_label}, giao phòng {team}. "
            "Tiêu đề do hệ thống sinh (không có phân tích LLM) — cần người phụ trách xác minh."
        ),
    }


def _llm_cluster_title(
    team: str, area: Any, topic: Optional[str], alerts: List[Dict[str, Any]]
) -> Optional[Dict[str, str]]:
    """Nhờ LLM đặt tên cụm. Trả None nếu LLM không dùng được — caller tự fallback."""
    samples = "\n".join(
        f"- {a.get('title')}: {str(a.get('description') or '')[:100]}" for a in alerts[:5]
    )
    prompt = f"""Bạn là một Quản lý Vận hành (Operations Manager).
Dưới đây là các sự cố (alerts) chủ đề "{topic}" thuộc phòng ban {team} tại khu vực {area}:
{samples}

Hãy đặt tên cho một Nhiệm vụ (Task) chung để giao cho phòng {team} xử lý dứt điểm.
Trả về JSON:
{{
  "title": "Tên Task ngắn gọn (dưới 10 chữ)",
  "summary": "Tóm tắt tình hình và hành động cần làm (2-3 câu)"
}}"""
    try:
        raw = call_llm("You are a helpful assistant.", prompt, "json_object")
        if not raw:
            return None
        parsed = json.loads(raw)
        title = str(parsed.get("title") or "").strip()
        if not title:
            return None
        return {"title": title[:120], "summary": str(parsed.get("summary") or "").strip()}
    except Exception as exc:
        print(f"[TaskAgent] LLM không đặt được tên cụm ({topic}@{area}): {str(exc)[:120]}")
        return None


def cluster_alerts_into_tasks() -> Dict[str, Any]:
    """Gom alert chưa có task thành task theo cụm (phòng ban, khu vực, chủ đề).

    Heuristic-first: việc gom là thuần rule, LLM chỉ đặt tên cho cụm mới và luôn có
    đường dự phòng. Một alert không bao giờ bị bỏ lại chỉ vì LLM hoặc DB lỗi tạm thời —
    lỗi được đếm và trả về, không nuốt.
    """
    start_time = time.time()
    db = get_db()

    try:
        res = (
            db.table("alerts")
            .select("*")
            .is_("task_id", "null")
            .in_("status", UNASSIGNED_ALERT_STATUSES)
            .execute()
        )
        unassigned_alerts = res.data or []
    except Exception as exc:
        log_agent_run(
            run_id=f"task_cluster_{int(time.time())}",
            agent_name="task_agent",
            status="failed",
            latency_ms=int((time.time() - start_time) * 1000),
            output_summary="Không đọc được alerts",
            error_message=str(exc)[:300],
        )
        return {"status": "error", "error": f"Failed to fetch alerts: {str(exc)}"}

    if not unassigned_alerts:
        return {
            "status": "success",
            "message": "No unassigned alerts found.",
            "tasks_created": 0,
            "alerts_assigned": 0,
            "clusters_failed": 0,
        }

    # Gom theo (phòng, khu vực, chủ đề) và giữ mức ưu tiên NẶNG NHẤT của cụm.
    clusters: Dict[tuple, List[Dict[str, Any]]] = {}
    cluster_priority: Dict[tuple, str] = {}
    for alert in unassigned_alerts:
        team = alert_department(alert, "CSKH")
        area = alert.get("area", "Unknown")
        topic = str(alert.get("topic") or "Other").strip() or "Other"
        key = (team, area, topic)
        clusters.setdefault(key, []).append(alert)

        priority = alert_priority(alert)
        if priority_rank(priority) > priority_rank(cluster_priority.get(key)):
            cluster_priority[key] = priority

    tasks_created = 0
    tasks_escalated = 0
    alerts_assigned = 0
    failures: List[str] = []

    for (team, area, topic), alerts in clusters.items():
        if not alerts:
            continue
        priority = cluster_priority.get((team, area, topic), "P2")
        task_id = None

        try:
            existing = _find_absorbing_task(db, team, area, topic)
            if existing:
                task_id = existing["id"]
                if escalate_task_priority(db, existing, priority, topic):
                    tasks_escalated += 1
            else:
                named = _llm_cluster_title(team, area, topic, alerts) or fallback_cluster_title(
                    team, area, topic, len(alerts)
                )
                task_id = find_or_create_cluster_task(
                    db, team, area, priority,
                    named["title"], named.get("summary", ""),
                    topic=topic,
                )
                if task_id:
                    tasks_created += 1
        except Exception as exc:
            failures.append(f"{team}/{area}/{topic}: {str(exc)[:120]}")
            print(f"[TaskAgent] Lỗi tạo task cụm {team}/{area}/{topic}: {exc}")
            continue

        if not task_id:
            failures.append(f"{team}/{area}/{topic}: insert không trả về id")
            continue

        try:
            db.table("alerts").update({"task_id": task_id}).in_(
                "id", [a["id"] for a in alerts]
            ).execute()
            alerts_assigned += len(alerts)
        except Exception as exc:
            failures.append(f"{team}/{area}/{topic}: gán alert lỗi — {str(exc)[:120]}")
            print(f"[TaskAgent] Lỗi cập nhật alerts: {exc}")

    # Log phải phản ánh đúng: cụm hỏng mà vẫn báo 'success' thì agent_run_logs vô dụng.
    status = "fallback" if failures else "success"
    summary = (
        f"Created {tasks_created} tasks, escalated {tasks_escalated}, "
        f"assigned {alerts_assigned} alerts, {len(failures)} cluster(s) failed."
    )
    log_agent_run(
        run_id=f"task_cluster_{int(time.time())}",
        agent_name="task_agent",
        status=status,
        latency_ms=int((time.time() - start_time) * 1000),
        output_summary=summary,
        error_message="; ".join(failures)[:500],
    )

    return {
        "status": "partial_success" if failures else "success",
        "tasks_created": tasks_created,
        "tasks_escalated": tasks_escalated,
        "alerts_assigned": alerts_assigned,
        "clusters_scanned": len(clusters),
        "clusters_failed": len(failures),
        "failures": failures[:10],
    }


def generate_daily_report(team: str) -> Dict[str, Any]:
    """Generate one report through the same insight/analyst path as orchestrator."""
    start_time = time.time()
    db = get_db()

    try:
        from agents.analyst_agent import analyze_root_cause
        from agents.insight_agent import generate_department_insights
        from agents.report_builder import build_department_report_markdown, store_department_report

        insights = generate_department_insights(team, hours=24)
        if insights.get("total_feedback", 0) <= 0:
            return {"status": "skipped", "message": f"No feedback for {team}"}
        analysis = analyze_root_cause(team, insights)
        content = build_department_report_markdown(team, insights, analysis)
        analysis_dict = analysis.get("analysis") or {}
        stored = store_department_report(
            db,
            team=team,
            report_date=datetime.now(timezone.utc).date().isoformat(),
            content=content,
            suggested_tasks=analysis_dict.get("action_items", []),
            root_cause_summary=analysis_dict.get("root_cause_summary", ""),
        )

        log_agent_run(
            run_id=f"report_{team}_{int(time.time())}",
            agent_name="task_agent",
            status="success",
            latency_ms=int((time.time() - start_time) * 1000),
            output_summary=f"Generated report for {team}"
        )
        return {"status": "success", "team": team, **stored}

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    res = cluster_alerts_into_tasks()
    print("Cluster Result:", res)
