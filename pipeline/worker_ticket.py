"""Ticket Workflow Worker — advance alert statuses open → in_progress → resolved.

Runs as the `backend-worker` Railway service. APScheduler ticks every
WORKER_TICKET_WORKFLOW_INTERVAL_SECONDS and calls advance_ticket_workflow().
It also redacts public Feedback past its retention deadline once a day at
03:00 Vietnam time (decision 0017).
"""

import os
import signal
import sys
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from services.live_stream import set_scheduler
from services.retention import redact_expired_public_feedback
from services.ticket_workflow import advance_ticket_workflow


def run_retention_redaction():
    """Daily job. Logs a count only, never row content."""
    try:
        count = redact_expired_public_feedback()
        print(f"[backend-worker] Retention: redacted {count} public feedback rows.", flush=True)
    except Exception as exc:
        # Type only: a driver error can quote the failing statement's values.
        print(f"[backend-worker] Retention redaction failed: {type(exc).__name__}", file=sys.stderr, flush=True)


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        advance_ticket_workflow,
        "interval",
        seconds=int(os.getenv("WORKER_TICKET_WORKFLOW_INTERVAL_SECONDS", "15")),
        id="auto_ticket_workflow",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(
        run_retention_redaction,
        "cron",
        hour=3,
        minute=0,
        # Railway containers run UTC; without this the job fires at 10:00 VN.
        timezone="Asia/Ho_Chi_Minh",
        id="retention_redact",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def main():
    scheduler = build_scheduler()
    set_scheduler(scheduler)
    scheduler.start()

    should_stop = False

    def stop(_signum, _frame):
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print("ticket-worker started.", flush=True)

    try:
        while not should_stop:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)
        set_scheduler(None)
        print("ticket-worker stopped.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ticket-worker failed: {exc}", file=sys.stderr, flush=True)
        raise
