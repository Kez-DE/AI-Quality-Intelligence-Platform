"""Insight Agent — tổng hợp metric feedback theo phòng ban (department).

Khác bản origin: import phẳng (insight_agent nằm trong pipeline/agents/).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import time

from agents.common import get_db, log_agent_run
from agents.router_agent import route_ticket
from agents.schemas import InsightOutput, TopArea, TopTopic, RecentSample


def _severity_to_int(sev: Any) -> int:
    """Chuẩn hoá severity về int 1..5. Hỗ trợ cả 'P5' lẫn 5."""
    if isinstance(sev, int):
        return sev
    if isinstance(sev, str):
        s = sev.upper().lstrip("P")
        try:
            return int(s)
        except ValueError:
            return 3
    return 3


def generate_department_insights(team: str, hours: int = 24) -> Dict[str, Any]:
    """Tổng hợp insight cho một phòng ban trong N giờ qua: tổng feedback,
    phân bố severity, top topics, vài sample gần nhất."""
    db = get_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        response = (
            db.table("feedback")
            .select("id, text, topic, severity, overall_risk, sentiment, created_at, area")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
        )
        all_feedback = response.data or []
    except Exception as exc:  # noqa: BLE001
        print(f"[insight_agent] Error fetching feedback: {exc}")
        all_feedback = []

    try:
        task_response = (
            db.table("tasks")
            .select("status,due_at")
            .eq("assigned_team", team)
            .execute()
        )
        team_tasks = task_response.data or []
    except Exception as exc:  # noqa: BLE001
        print(f"[insight_agent] Error fetching tasks: {exc}")
        team_tasks = []

    task_status = {"open": 0, "in_progress": 0, "resolved": 0}
    overdue_tasks = 0
    now = datetime.now(timezone.utc)
    for task in team_tasks:
        status = str(task.get("status") or "open")
        task_status[status] = task_status.get(status, 0) + 1
        due_at = str(task.get("due_at") or "")
        if status != "resolved" and due_at:
            try:
                due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                if due < now:
                    overdue_tasks += 1
            except ValueError:
                pass

    # Lọc feedback thuộc về team (theo routing table)
    team_feedback = [
        f
        for f in all_feedback
        if route_ticket(
            f.get("topic", ""),
            f"P{f['overall_risk']}" if f.get("overall_risk") else f.get("severity", 3),
            f.get("sentiment"),
            log_run=False,
        )["team"] == team
    ]

    start_time = time.time()
    total_feedback = len(team_feedback)
    
    if total_feedback == 0:
        output = InsightOutput(
            team=team,
            period_hours=hours,
            total_feedback=0,
            severity_distribution={"CRITICAL": 0, "WARNING": 0, "WATCH": 0, "INFO": 0},
            sentiment_distribution={"negative": 0, "neutral": 0, "positive": 0},
            task_status_distribution=task_status,
            overdue_tasks=overdue_tasks,
            top_topics=[],
            top_areas=[],
            recent_samples=[]
        )
        latency_ms = int((time.time() - start_time) * 1000)
        log_agent_run(
            run_id=f"insight_{int(time.time())}",
            agent_name="insight_agent",
            status="success",
            latency_ms=latency_ms,
            output_summary="0 feedback found.",
            input_hash=f"{team}_{hours}",
            team=team
        )
        return output.model_dump()

    severity_dist = {"CRITICAL": 0, "WARNING": 0, "WATCH": 0, "INFO": 0}
    sentiment_dist = {"negative": 0, "neutral": 0, "positive": 0}
    topic_counts: Dict[str, int] = {}
    area_counts: Dict[str, int] = {}

    for f in team_feedback:
        sev_int = _severity_to_int(f.get("overall_risk") or f.get("severity"))
        if sev_int >= 5:
            severity_dist["CRITICAL"] += 1
        elif sev_int == 4:
            severity_dist["WARNING"] += 1
        elif sev_int == 3:
            severity_dist["WATCH"] += 1
        else:
            severity_dist["INFO"] += 1

        topic = f.get("topic", "Unknown")
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        sentiment = str(f.get("sentiment") or "neutral").lower()
        sentiment_dist[sentiment] = sentiment_dist.get(sentiment, 0) + 1
        area = str(f.get("area") or "Unknown")
        area_counts[area] = area_counts.get(area, 0) + 1

    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    sorted_areas = sorted(area_counts.items(), key=lambda x: x[1], reverse=True)
    samples = []
    for f in team_feedback[:5]:
        text = str(f.get("text") or "").strip()
        if not text:
            continue
        samples.append(RecentSample(id=f.get("id"), text=text, area=f.get("area")))

    output = InsightOutput(
        team=team,
        period_hours=hours,
        total_feedback=total_feedback,
        severity_distribution=severity_dist,
        sentiment_distribution=sentiment_dist,
        task_status_distribution=task_status,
        overdue_tasks=overdue_tasks,
        top_topics=[TopTopic(topic=t[0], count=t[1]) for t in sorted_topics[:5]],
        top_areas=[TopArea(area=a[0], count=a[1]) for a in sorted_areas[:5]],
        recent_samples=samples
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    log_agent_run(
        run_id=f"insight_{int(time.time())}",
        agent_name="insight_agent",
        status="success",
        latency_ms=latency_ms,
        output_summary=f"{total_feedback} feedbacks aggregated.",
        input_hash=f"{team}_{hours}",
        team=team
    )

    return output.model_dump()


if __name__ == "__main__":
    print(generate_department_insights("Safety", 24))
