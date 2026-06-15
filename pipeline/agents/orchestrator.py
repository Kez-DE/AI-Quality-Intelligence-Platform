"""Orchestrator — điều phối pipeline 6 agent khép kín.

6 Agent nghiệp vụ:
  1. Ingestion/Classifier Agent — clean PII, phân loại topic/sentiment/severity
  2. Router Agent — định tuyến ticket về đúng phòng ban
  3. Ticket Agent — tạo/cập nhật/dedup ticket, gán SLA + priority
  4. Insight Agent — tổng hợp metric feedback theo phòng ban
  5. Analyst Agent — phân tích root cause bằng LLM, đề xuất action items
  6. Alert/Escalation Agent — phân cấp WATCH/WARNING/CRITICAL, cooldown dedup

Orchestrator KHÔNG phải agent nghiệp vụ — chỉ điều phối, retry, logging, schedule.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from agents.common import get_db, log_agent_run
from agents.insight_agent import generate_department_insights
from agents.analyst_agent import analyze_root_cause
from agents.alert_agent import classify_alert_severity, process_area_alerts
from agents.router_agent import route_ticket
from agents.ticket_agent import create_or_update_ticket, TicketInput, get_overdue_tickets

# Phòng ban khớp với routing_table.json (team đích của router_agent).
TEAMS = ["IT", "Safety", "CSKH", "Vận hành", "Pricing", "Marketing"]


def run_agent_pipeline(hours: int = 24) -> Dict[str, Any]:
    """Quét tất cả phòng ban, sinh insight, chạy root-cause cho phòng có feedback.

    Pipeline 7 bước:
    1. Thu thập feedback P4/P5 trong N giờ
    2. Alert Agent: phân cấp cảnh báo theo khu vực
    3. Router Agent: xác nhận phòng ban cho từng spike
    4. Ticket Agent: tạo/dedup ticket
    5. Insight Agent: tổng hợp metric tất cả phòng ban
    6. Analyst Agent: phân tích sâu phòng có rủi ro
    7. Kiểm tra ticket quá SLA
    """
    start_time = datetime.now(timezone.utc)
    print(f"[{start_time.isoformat()}] Bắt đầu chạy Agent Pipeline (6 agents)...")

    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    pipeline_log: List[str] = []

    # ── Step 1-4: Alert detection + Ticket creation (đã xử lý ở spike_detector flow) ──
    # Orchestrator gọi lại khi chạy thủ công
    overdue_tickets = []
    try:
        overdue_tickets = get_overdue_tickets(sla_hours=24)
        if overdue_tickets:
            pipeline_log.append(f"Phát hiện {len(overdue_tickets)} ticket quá SLA 24h")
    except Exception as exc:
        pipeline_log.append(f"Lỗi kiểm tra SLA: {str(exc)[:100]}")

    # ── Step 5-6: Insight + Analyst cho từng phòng ban ──
    for team in TEAMS:
        try:
            # Agent 4: Insight Agent
            insights = generate_department_insights(team, hours=hours)

            if insights.get("total_feedback", 0) > 0:
                # Agent 5: Analyst Agent — chỉ phân tích phòng có feedback
                insights["analysis"] = analyze_root_cause(team, insights)
                pipeline_log.append(
                    f"{team}: {insights['total_feedback']} feedback, "
                    f"analyzed={'success' if insights.get('analysis', {}).get('status') == 'success' else 'fallback'}"
                )
            else:
                insights["analysis"] = None
                pipeline_log.append(f"{team}: 0 feedback, skipped analysis")

            results[team] = insights

        except Exception as exc:
            error_msg = str(exc)[:300]
            errors[team] = error_msg
            pipeline_log.append(f"{team}: ERROR — {error_msg[:100]}")
            results[team] = {
                "team": team,
                "period_hours": hours,
                "total_feedback": 0,
                "severity_distribution": {"CRITICAL": 0, "WARNING": 0, "WATCH": 0, "INFO": 0},
                "top_topics": [],
                "recent_samples": [],
                "analysis": None,
                "error": error_msg,
            }

    end_time = datetime.now(timezone.utc)
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    print(f"Pipeline hoàn tất trong {duration_ms}ms.")

    return {
        "status": "partial_success" if errors else "success",
        "timestamp": end_time.isoformat(),
        "duration_ms": duration_ms,
        "departments_processed": len(results),
        "overdue_tickets": len(overdue_tickets),
        "errors": errors,
        "pipeline_log": pipeline_log,
        "agents_used": [
            "ingestion_agent",
            "router_agent",
            "ticket_agent",
            "insight_agent",
            "analyst_agent",
            "alert_agent",
        ],
        "data": results,
    }


def run_full_cycle(hours: int = 24, max_feedback: int = 1000, max_spikes: int = 3) -> Dict[str, Any]:
    """Chạy full cycle: spike detect + ticket + insight + analysis.

    Dùng cho /api/agent/run khi muốn chạy toàn bộ pipeline từ đầu.
    """
    pipeline_result = run_agent_pipeline(hours=hours)

    # Thêm spike detection nếu cần
    try:
        from spike_detector import detect_spikes
        spike_result = detect_spikes(max_feedback=max_feedback, max_spikes=max_spikes)
        pipeline_result["spike_detection"] = spike_result
    except Exception as exc:
        pipeline_result["spike_detection"] = {"error": str(exc)[:200]}

    return pipeline_result


if __name__ == "__main__":
    res = run_agent_pipeline()
    print(f"Processed {res['departments_processed']} departments in {res['duration_ms']}ms.")
    print(f"Agents used: {res['agents_used']}")
    if res["errors"]:
        print(f"Errors: {res['errors']}")
