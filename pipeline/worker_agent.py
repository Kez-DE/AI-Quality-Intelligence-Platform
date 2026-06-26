"""Agent Orchestrator Worker — runs the full multi-agent pipeline periodically.

Runs as the `agent-worker` Railway service. APScheduler triggers
run_agent_pipeline() every WORKER_AGENT_INTERVAL_SECONDS (default 300s).

Set WORKER_AGENT_ENABLED=false to suspend without redeploying (saves LLM cost).
"""

import os
import signal
import sys
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from agents.orchestrator import run_agent_pipeline

INTERVAL = int(os.getenv("WORKER_AGENT_INTERVAL_SECONDS", "300"))
HOURS    = int(os.getenv("WORKER_AGENT_HOURS", "24"))
ENABLED  = os.getenv("WORKER_AGENT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def run_alert_pipeline():
    if not ENABLED:
        print("[agent-worker] WORKER_AGENT_ENABLED=false — skipping alert pipeline run.", flush=True)
        return
    print(f"[agent-worker] Starting alert pipeline (last 1h)...", flush=True)
    try:
        result = run_agent_pipeline(hours=1, run_alert=True, run_report=False)
        print(f"[agent-worker] Alert pipeline done: {result.get('summary', result)}", flush=True)
    except Exception as exc:
        print(f"[agent-worker] Alert pipeline error: {exc}", file=sys.stderr, flush=True)


def run_report_pipeline():
    if not ENABLED:
        print("[agent-worker] WORKER_AGENT_ENABLED=false — skipping report pipeline run.", flush=True)
        return
    print(f"[agent-worker] Starting report pipeline (last {HOURS}h)...", flush=True)
    try:
        result = run_agent_pipeline(hours=HOURS, run_alert=False, run_report=True)
        print(f"[agent-worker] Report pipeline done: {result.get('summary', result)}", flush=True)
    except Exception as exc:
        print(f"[agent-worker] Report pipeline error: {exc}", file=sys.stderr, flush=True)


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_alert_pipeline,
        "interval",
        seconds=INTERVAL,
        id="alert_pipeline",
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(
        run_report_pipeline,
        "cron",
        hour="9,14",
        minute="0",
        id="report_pipeline",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def main():
    scheduler = build_scheduler()
    scheduler.start()

    should_stop = False

    def stop(_signum, _frame):
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(f"agent-worker started. Alert every {INTERVAL}s (1h). Report at 09:00, 14:00 ({HOURS}h).", flush=True)

    try:
        while not should_stop:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)
        print("agent-worker stopped.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"agent-worker failed: {exc}", file=sys.stderr, flush=True)
        raise
