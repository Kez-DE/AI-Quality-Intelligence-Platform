"""Ticket Workflow Worker — advance alert statuses open → in_progress → resolved.

Runs as the `backend-worker` Railway service. APScheduler ticks every
WORKER_TICKET_WORKFLOW_INTERVAL_SECONDS and calls advance_ticket_workflow().
"""

import os
import signal
import sys
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from services.live_stream import set_scheduler
from services.ticket_workflow import advance_ticket_workflow


def main():
    scheduler = BackgroundScheduler()
    set_scheduler(scheduler)
    scheduler.add_job(
        advance_ticket_workflow,
        "interval",
        seconds=int(os.getenv("WORKER_TICKET_WORKFLOW_INTERVAL_SECONDS", "5")),
        id="auto_ticket_workflow",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
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
