"""Orchestrator — điều phối multi-agent: quét từng phòng ban -> insight -> root-cause.

Khác bản origin: import phẳng (pipeline/agents) thay vì backend.pipeline.agents.
Có thể gọi định kỳ qua APScheduler hoặc thủ công qua /api/agent/run.
"""

from datetime import datetime

from agents.insight_agent import generate_department_insights
from agents.analyst_agent import analyze_root_cause

# Phòng ban khớp với routing_table.json (team đích của router_agent).
TEAMS = ["IT", "Safety", "CSKH", "Vận hành", "Pricing", "Marketing"]


def run_agent_pipeline(hours: int = 24):
    """Quét tất cả phòng ban, sinh insight, chạy root-cause cho phòng có feedback."""
    print(f"[{datetime.utcnow().isoformat()}] Bắt đầu chạy Agent Pipeline...")
    results = {}
    errors = {}

    for team in TEAMS:
        try:
            insights = generate_department_insights(team, hours=hours)
            if insights.get("total_feedback", 0) > 0:
                insights["analysis"] = analyze_root_cause(team, insights)
            results[team] = insights
        except Exception as exc:  # noqa: BLE001 - không để 1 team làm hỏng cả 6 agent
            errors[team] = str(exc)[:300]
            results[team] = {
                "team": team,
                "period_hours": hours,
                "total_feedback": 0,
                "severity_distribution": {"CRITICAL": 0, "WARNING": 0, "WATCH": 0, "INFO": 0},
                "top_topics": [],
                "recent_samples": [],
                "analysis": None,
                "error": errors[team],
            }

    print("Pipeline hoàn tất.")
    return {
        "status": "partial_success" if errors else "success",
        "timestamp": datetime.utcnow().isoformat(),
        "departments_processed": len(results),
        "errors": errors,
        "data": results,
    }


if __name__ == "__main__":
    res = run_agent_pipeline()
    print("Processed", res["departments_processed"], "departments.")
