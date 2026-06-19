"""Insight Agent — tổng hợp metric feedback theo phòng ban (department).

Khác bản origin: import phẳng (insight_agent nằm trong pipeline/agents/).
"""

from datetime import datetime, timedelta
from typing import Any, Dict

import time

from agents.common import get_db, log_agent_run
from agents.router_agent import route_ticket
from agents.schemas import InsightOutput, TopTopic, RecentSample


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
            .select("id, text, topic, severity, sentiment, created_at, area")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
        )
        all_feedback = response.data or []
    except Exception as exc:  # noqa: BLE001
        print(f"[insight_agent] Error fetching feedback: {exc}")
        all_feedback = []

    # Lọc feedback thuộc về team (theo routing table)
    team_feedback = [
        f
        for f in all_feedback
        if route_ticket(
            f.get("topic", ""), f.get("severity", 3), f.get("sentiment"), log_run=False
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
            top_topics=[],
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
    topic_counts: Dict[str, int] = {}

    for f in team_feedback:
        sev_int = _severity_to_int(f.get("severity"))
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

    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    samples = []
    for f in team_feedback[:3]:
        text = str(f.get("text") or "").strip()
        if not text:
            continue
        samples.append(RecentSample(id=f.get("id"), text=text, area=f.get("area")))

    output = InsightOutput(
        team=team,
        period_hours=hours,
        total_feedback=total_feedback,
        severity_distribution=severity_dist,
        top_topics=[TopTopic(topic=t[0], count=t[1]) for t in sorted_topics[:5]],
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
