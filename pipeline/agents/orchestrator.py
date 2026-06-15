"""Orchestrator — điều phối multi-agent: quét từng phòng ban -> insight -> root-cause.

Khác bản origin: import phẳng (pipeline/agents) thay vì backend.pipeline.agents.
Có thể gọi định kỳ qua APScheduler hoặc thủ công qua /api/agent/run.
"""

from datetime import datetime, timedelta

from agents.common import get_db, log_agent_run
from agents.insight_agent import generate_department_insights
from agents.analyst_agent import analyze_root_cause
from agents.alert_agent import process_area_alerts
from agents.router_agent import route_ticket
from agents.ticket_agent import create_or_update_ticket
from llm_agent import analyze_spike

# Phòng ban khớp với routing_table.json (team đích của router_agent).
TEAMS = ["IT", "Safety", "CSKH", "Vận hành", "Pricing", "Marketing"]


def run_agent_pipeline(hours: int = 24):
    """Orchestrator chạy vòng lặp 7 bước."""
    print(f"[{datetime.utcnow().isoformat()}] Bắt đầu chạy Agent Pipeline...")
    results = {}
    errors = {}
    db = get_db()
    
    # Bước 1 & 2: Quét feedback P4/P5 và tìm spike
    since = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    try:
        response = db.table("feedback") \
            .select("id, text, area, severity, topic") \
            .gte("created_at", since) \
            .in_("severity", ["P4", "P5", 4, 5]) \
            .order("created_at", desc=True) \
            .execute()
        
        feedbacks = response.data or []
        area_feedbacks = {}
        for f in feedbacks:
            area = f.get("area", "Unknown")
            if area not in area_feedbacks:
                area_feedbacks[area] = []
            area_feedbacks[area].append(f)
            
        alerts_created = []
        for area, fbs in area_feedbacks.items():
            # Bước 2: Alert Agent đánh giá severity
            alert_decision = process_area_alerts(area, fbs)
            if alert_decision.get("action") == "create":
                # Bước 3: Phân tích root cause cho spike
                texts = [f.get("text", "") for f in fbs[:20]]
                spike_analysis = analyze_spike(area, texts)
                
                # Bước 4: Định tuyến
                top_topic = fbs[0].get("topic", "Unknown") if fbs else "Unknown"
                route_res = route_ticket(top_topic, alert_decision.get("severity"))
                
                # Bước 5: Tạo ticket
                ticket_res = create_or_update_ticket(
                    area=area,
                    title=spike_analysis.get("title", f"Spike tại {area}"),
                    description=spike_analysis.get("description", "") + f"\n\n**Action Plan:** {spike_analysis.get('action', '')}\n**Assigned Team:** {route_res.get('team')}",
                    severity=alert_decision.get("severity", "CRITICAL"),
                    team=route_res.get("team"),
                    sla_hours=route_res.get("sla_hours", 24)
                )
                alerts_created.append(ticket_res)
                
        results["alerts_created"] = alerts_created
                
    except Exception as exc:
        print(f"[Orchestrator] Error processing alerts: {exc}")
        errors["alerts"] = str(exc)

    # Bước 6 & 7: Insight & Phân tích sâu cho tất cả phòng ban
    for team in TEAMS:
        try:
            insights = generate_department_insights(team, hours=hours)
            if insights.get("total_feedback", 0) > 0:
                insights["analysis"] = analyze_root_cause(team, insights)
            results[team] = insights
        except Exception as exc:  # noqa: BLE001
            errors[team] = str(exc)[:300]
            results[team] = {"team": team, "error": errors[team]}

    print("Pipeline hoàn tất.")
    return {
        "status": "partial_success" if errors else "success",
        "timestamp": datetime.utcnow().isoformat(),
        "departments_processed": len(TEAMS),
        "errors": errors,
        "data": results,
    }


if __name__ == "__main__":
    res = run_agent_pipeline()
    print("Processed", res["departments_processed"], "departments.")
