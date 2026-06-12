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

    for team in TEAMS:
        insights = generate_department_insights(team, hours=hours)
        if insights.get("total_feedback", 0) > 0:
            analysis = analyze_root_cause(team, insights)
            insights["analysis"] = analysis
        results[team] = insights

    print("Pipeline hoàn tất.")
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "departments_processed": len(results),
        "data": results,
    }


if __name__ == "__main__":
    res = run_agent_pipeline()
    print("Processed", res["departments_processed"], "departments.")
