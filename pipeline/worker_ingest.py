"""Ingest Worker — live stream batch ingestion from dataset.

Runs as the `ingest-worker` Railway service. Starts live stream when
LIVE_STREAM_ENABLED=true; APScheduler handles the per-interval ticks.
"""

import os
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler

from services.live_stream import DEFAULT_MAX_SPIKES, set_scheduler, start_live_stream


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def main():
    scheduler = BackgroundScheduler()
    set_scheduler(scheduler)
    scheduler.start()

    if _env_bool("LIVE_STREAM_ENABLED", False):
        start_live_stream(
            batch_size=int(os.getenv("LIVE_STREAM_BATCH_SIZE", "150")),
            interval_seconds=int(os.getenv("LIVE_STREAM_INTERVAL_SECONDS", "5")),
            loop=_env_bool("LIVE_STREAM_LOOP", False),
            reset=_env_bool("LIVE_STREAM_RESET_ON_START", False),
            auto_ticket=_env_bool("AUTO_TICKET_ENABLED", True),
            ticket_every_batches=int(os.getenv("AUTO_TICKET_EVERY_BATCHES", "2")),
            ticket_max_spikes=int(os.getenv("AUTO_TICKET_MAX_SPIKES", str(DEFAULT_MAX_SPIKES))),
        )

    should_stop = False

    def stop(_signum, _frame):
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print("ingest-worker started.", flush=True)

    try:
        while not should_stop:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)
        set_scheduler(None)
        print("ingest-worker stopped.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ingest-worker failed: {exc}", file=sys.stderr, flush=True)
        raise
