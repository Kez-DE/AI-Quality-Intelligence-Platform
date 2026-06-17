import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from core.paths import DEFAULT_DATA_FILE
from ingest import ingest_dataset

scheduler: BackgroundScheduler | None = None
live_stream_lock = Lock()
live_stream_tick_lock = Lock()
live_stream_state: dict[str, Any] = {
    "running": False,
    "offset": 0,
    "batch_size": int(os.getenv("LIVE_STREAM_BATCH_SIZE", "150")),
    "interval_seconds": int(os.getenv("LIVE_STREAM_INTERVAL_SECONDS", "10")),
    "loop": os.getenv("LIVE_STREAM_LOOP", "false").lower() == "true",
    "auto_ticket": os.getenv("AUTO_TICKET_ENABLED", "true").lower() == "true",
    "ticket_every_batches": int(os.getenv("AUTO_TICKET_EVERY_BATCHES", "10")),
    "ticket_max_feedback": int(os.getenv("AUTO_TICKET_MAX_FEEDBACK", "1000")),
    "ticket_max_spikes": int(os.getenv("AUTO_TICKET_MAX_SPIKES", "1")),
    "ticket_running": False,
    "batches_ingested": 0,
    "last_ticket_result": None,
    "last_ticket_error": None,
    "last_ticket_at": None,
    "last_ticket_batch": None,
    "last_result": None,
    "last_error": None,
}


def set_scheduler(active_scheduler: BackgroundScheduler | None):
    global scheduler
    scheduler = active_scheduler


def run_auto_ticket_detection():
    try:
        from spike_detector import detect_spikes

        with live_stream_lock:
            max_feedback = int(live_stream_state["ticket_max_feedback"])
            max_spikes = int(live_stream_state["ticket_max_spikes"])
            live_stream_state["last_ticket_error"] = None

        result = detect_spikes(max_feedback=max_feedback, max_spikes=max_spikes)
        with live_stream_lock:
            live_stream_state["last_ticket_result"] = result
            live_stream_state["last_ticket_error"] = None
            live_stream_state["last_ticket_at"] = datetime.now(timezone.utc).isoformat()
            live_stream_state["last_ticket_batch"] = live_stream_state["batches_ingested"]
    except Exception as exc:
        with live_stream_lock:
            live_stream_state["last_ticket_error"] = str(exc)
    finally:
        with live_stream_lock:
            live_stream_state["ticket_running"] = False


def live_stream_tick():
    if not live_stream_tick_lock.acquire(blocking=False):
        return
    try:
        _live_stream_tick()
    finally:
        live_stream_tick_lock.release()


def _live_stream_tick():
    dataset_file = os.getenv("REAL_DATA_FILE", DEFAULT_DATA_FILE)
    with live_stream_lock:
        if not live_stream_state["running"]:
            return
        offset = int(live_stream_state["offset"])
        batch_size = int(live_stream_state["batch_size"])

    try:
        result = ingest_dataset(
            dataset_file,
            limit=batch_size,
            batch_size=batch_size,
            offset=offset,
        )
        with live_stream_lock:
            live_stream_state["last_result"] = result
            live_stream_state["last_error"] = None
            if result.get("success"):
                live_stream_state["batches_ingested"] += 1
                should_detect = (
                    live_stream_state["auto_ticket"]
                    and not live_stream_state["ticket_running"]
                    and live_stream_state["batches_ingested"] % int(live_stream_state["ticket_every_batches"]) == 0
                )
                if should_detect:
                    live_stream_state["ticket_running"] = True
                if result.get("complete"):
                    if live_stream_state["loop"]:
                        live_stream_state["offset"] = 0
                    else:
                        live_stream_state["running"] = False
                        if scheduler and scheduler.get_job("live_feedback_stream"):
                            scheduler.remove_job("live_feedback_stream")
                else:
                    live_stream_state["offset"] = result.get("next_offset", offset + batch_size)
            else:
                live_stream_state["running"] = False
                should_detect = False
        if should_detect and scheduler:
            scheduler.add_job(
                run_auto_ticket_detection,
                id="auto_ticket_detection",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
    except Exception as exc:
        with live_stream_lock:
            live_stream_state["last_error"] = str(exc)
            live_stream_state["running"] = False
        if scheduler and scheduler.get_job("live_feedback_stream"):
            scheduler.remove_job("live_feedback_stream")


def start_live_stream(
    batch_size: int,
    interval_seconds: int,
    loop: bool,
    reset: bool = False,
    auto_ticket: bool = True,
    ticket_every_batches: int = 10,
    ticket_max_spikes: int = 1,
):
    if not scheduler:
        raise ValueError("Scheduler is not initialized")
    with live_stream_lock:
        if reset:
            live_stream_state["offset"] = 0
            live_stream_state["batches_ingested"] = 0
            live_stream_state["last_ticket_result"] = None
            live_stream_state["last_ticket_error"] = None
            live_stream_state["last_ticket_at"] = None
            live_stream_state["last_ticket_batch"] = None
        live_stream_state["batch_size"] = batch_size
        live_stream_state["interval_seconds"] = interval_seconds
        live_stream_state["loop"] = loop
        live_stream_state["auto_ticket"] = auto_ticket
        live_stream_state["ticket_every_batches"] = ticket_every_batches
        live_stream_state["ticket_max_spikes"] = ticket_max_spikes
        live_stream_state["running"] = True
        live_stream_state["ticket_running"] = False
        live_stream_state["last_error"] = None

    scheduler.add_job(
        live_stream_tick,
        "interval",
        seconds=interval_seconds,
        id="live_feedback_stream",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
    return get_live_stream_status()


def stop_live_stream():
    with live_stream_lock:
        live_stream_state["running"] = False
    if scheduler and scheduler.get_job("live_feedback_stream"):
        scheduler.remove_job("live_feedback_stream")
    return get_live_stream_status()


def get_live_stream_status():
    with live_stream_lock:
        return dict(live_stream_state)
