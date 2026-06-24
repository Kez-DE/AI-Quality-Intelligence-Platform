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
import os

from agents.common import get_db, log_agent_run
from agents.insight_agent import generate_department_insights
from agents.analyst_agent import analyze_root_cause
from agents.report_builder import build_department_report_markdown, store_department_report
from agents.ticket_agent import get_overdue_tickets
from agents.task_agent import cluster_alerts_into_tasks
from departments import DEPARTMENTS

# Phòng ban khớp với routing_table.json (team đích của router_agent).
TEAMS = list(DEPARTMENTS)


def _agent_enabled(name: str) -> bool:
    """Cờ bật/tắt từng agent qua env, mặc định bật (giữ nguyên hành vi cũ).

    Tắt một agent để cô lập debug hoặc tiết kiệm chi phí LLM mà không cần
    redeploy cả cụm. Ví dụ: AGENT_ANALYST_ENABLED=false tắt root-cause LLM.
    Các cờ: AGENT_ALERT_ENABLED, AGENT_TASK_ENABLED, AGENT_INSIGHT_ENABLED,
    AGENT_ANALYST_ENABLED.
    """
    val = os.getenv(f"AGENT_{name.upper()}_ENABLED")
    if val is None:
        return True
    return val.strip().lower() in {"1", "true", "yes", "on"}


def run_agent_pipeline(hours: int = 24) -> Dict[str, Any]:
    """Quét tất cả phòng ban, sinh insight, chạy root-cause cho phòng có feedback.

    Pipeline 7 bước:
    1. Thu thập feedback P4/P5 trong N giờ
    2. Alert Agent: phân cấp cảnh báo theo khu vực
    3. Router Agent: xác nhận phòng ban cho từng spike
    4. Ticket Agent: tạo/dedup ticket
    5. Task Agent: gom cụm alerts thành tasks
    6. Insight Agent: tổng hợp metric tất cả phòng ban
    7. Analyst Agent: phân tích sâu phòng có rủi ro + sinh báo cáo
    """
    start_time = datetime.now(timezone.utc)
    print(f"[{start_time.isoformat()}] Bắt đầu chạy Agent Pipeline (6 agents)...")

    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    pipeline_log: List[str] = []
    db = get_db()

    # ── Step 1-4: Alert detection + Ticket creation ──
    alerts_created_count = 0
    if not _agent_enabled("alert"):
        pipeline_log.append("Alert agent disabled (AGENT_ALERT_ENABLED=false) — skipped spike→ticket")
    else:
        try:
            # Dùng cùng một detector với live stream để routing/threshold không bị lệch.
            from spike_detector import detect_spikes

            spike_result = detect_spikes(hours=hours, max_feedback=5000, max_spikes=20)
            alerts_created_count = int(spike_result.get("alerts_created", 0))
            results["spike_detection"] = spike_result
            pipeline_log.append(
                f"Alerts: {alerts_created_count} ticket(s), "
                f"{spike_result.get('groups_scanned', 0)} routing group(s) scanned"
            )
        except Exception as exc:
            error_msg = str(exc)[:200]
            pipeline_log.append(f"Alert processing error: {error_msg}")
            errors["alerts"] = error_msg

    # ── Step 5: Task Agent — gom cụm alerts thành tasks ──
    if not _agent_enabled("task"):
        pipeline_log.append("Task agent disabled (AGENT_TASK_ENABLED=false) — skipped")
    else:
        try:
            cluster_res = cluster_alerts_into_tasks()
            results["tasks_clustered"] = cluster_res
            pipeline_log.append(f"Tasks clustered: {cluster_res.get('tasks_created', 0)} task(s)")
        except Exception as exc:
            pipeline_log.append(f"Task clustering error: {str(exc)[:100]}")
            errors["task_clustering"] = str(exc)[:200]

    # ── Step 5.5: Kiểm tra ticket quá SLA ──
    overdue_tickets = []
    try:
        overdue_tickets = get_overdue_tickets(sla_hours=24)
        if overdue_tickets:
            pipeline_log.append(f"Phát hiện {len(overdue_tickets)} ticket quá SLA 24h")
    except Exception as exc:
        pipeline_log.append(f"Lỗi kiểm tra SLA: {str(exc)[:100]}")

    # ── Step 6-7: Insight + Analyst cho từng phòng ban ──
    insight_on = _agent_enabled("insight")
    analyst_on = _agent_enabled("analyst")
    if not insight_on:
        pipeline_log.append("Insight agent disabled (AGENT_INSIGHT_ENABLED=false) — skipped Insight+Analyst")
    for team in (TEAMS if insight_on else []):
        try:
            # Agent 4: Insight Agent
            insights = generate_department_insights(team, hours=hours)

            if insights.get("total_feedback", 0) > 0:
                analysis_res = (
                    analyze_root_cause(team, insights)
                    if analyst_on
                    else {"status": "disabled", "analysis": None}
                )
                insights["analysis"] = analysis_res

                md = build_department_report_markdown(team, insights, analysis_res)
                try:
                    _analysis = (analysis_res.get("analysis") or {}) if isinstance(analysis_res, dict) else {}
                    _suggested = _analysis.get("action_items") or []
                    _root_cause = _analysis.get("root_cause_summary") or None
                    store_result = store_department_report(
                        db,
                        team=team,
                        report_date=datetime.now(timezone.utc).date().isoformat(),
                        content=md,
                        suggested_tasks=_suggested,
                        root_cause_summary=_root_cause,
                    )
                    if not store_result.get("stored"):
                        pipeline_log.append(f"{team}: approved report retained")
                except Exception as exc:
                    errors[f"report:{team}"] = str(exc)[:200]
                    pipeline_log.append(f"{team}: report storage error — {str(exc)[:100]}")

                pipeline_log.append(
                    f"{team}: {insights['total_feedback']} feedback, "
                    f"analyzed={analysis_res.get('status', 'unknown')}"
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
        "alerts_created": alerts_created_count,
        "tasks_clustered": results.get("tasks_clustered", {}),
        "overdue_tickets": len(overdue_tickets),
        "errors": errors,
        "pipeline_log": pipeline_log,
        "agents_used": [
            "ingestion_agent",
            "router_agent",
            "ticket_agent",
            "task_agent",
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


    return pipeline_result


if __name__ == "__main__":
    res = run_agent_pipeline()
    print(f"Processed {res['departments_processed']} departments in {res['duration_ms']}ms.")
    print(f"Agents used: {res['agents_used']}")
    if res["errors"]:
        print(f"Errors: {res['errors']}")
