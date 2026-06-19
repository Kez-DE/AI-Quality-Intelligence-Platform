import os
import signal
import sys
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from services.live_stream import set_scheduler, start_live_stream
from services.ticket_workflow import advance_ticket_workflow


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    set_scheduler(scheduler)

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

    return scheduler


def start_configured_live_stream():
    if not _env_bool("LIVE_STREAM_ENABLED", False):
        return

    start_live_stream(
        batch_size=int(os.getenv("LIVE_STREAM_BATCH_SIZE", "150")),
        interval_seconds=int(os.getenv("LIVE_STREAM_INTERVAL_SECONDS", "10")),
        loop=_env_bool("LIVE_STREAM_LOOP", False),
        reset=_env_bool("LIVE_STREAM_RESET_ON_START", False),
        auto_ticket=_env_bool("AUTO_TICKET_ENABLED", True),
        ticket_every_batches=int(os.getenv("AUTO_TICKET_EVERY_BATCHES", "10")),
        ticket_max_spikes=int(os.getenv("AUTO_TICKET_MAX_SPIKES", "1")),
    )


def main():
    scheduler = build_scheduler()
    should_stop = False

    def stop(_signum, _frame):
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    scheduler.start()
    start_configured_live_stream()
    print("Backend worker started.", flush=True)

    try:
        while not should_stop:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)
        set_scheduler(None)
        print("Backend worker stopped.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Backend worker failed: {exc}", file=sys.stderr, flush=True)
        raise
