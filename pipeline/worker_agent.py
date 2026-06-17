"""Agent Orchestrator Worker — runs the full multi-agent pipeline periodically.

Runs as the `agent-worker` Railway service. APScheduler triggers
run_agent_pipeline() every WORKER_AGENT_INTERVAL_SECONDS (default 300s).

Set WORKER_AGENT_ENABLED=false to suspend without redeploying (saves LLM cost).
"""

import os
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler

from agents.orchestrator import run_agent_pipeline

INTERVAL = int(os.getenv("WORKER_AGENT_INTERVAL_SECONDS", "300"))
HOURS    = int(os.getenv("WORKER_AGENT_HOURS", "24"))
ENABLED  = os.getenv("WORKER_AGENT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def run_pipeline():
    if not ENABLED:
        print("[agent-worker] WORKER_AGENT_ENABLED=false — skipping pipeline run.", flush=True)
        return
    print(f"[agent-worker] Starting agent pipeline (last {HOURS}h)...", flush=True)
    try:
        result = run_agent_pipeline(hours=HOURS)
        print(f"[agent-worker] Pipeline done: {result.get('summary', result)}", flush=True)
    except Exception as exc:
        print(f"[agent-worker] Pipeline error: {exc}", file=sys.stderr, flush=True)


def main():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline,
        "interval",
        seconds=INTERVAL,
        id="agent_pipeline",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    should_stop = False

    def stop(_signum, _frame):
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(f"agent-worker started. Pipeline every {INTERVAL}s, window={HOURS}h.", flush=True)

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
