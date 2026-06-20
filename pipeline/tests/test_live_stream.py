import os
import sys
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.live_stream as live_stream


class FakeScheduler:
    def __init__(self):
        self.jobs = {}

    def add_job(self, func, *args, id=None, **kwargs):
        self.jobs[id] = {"func": func, "args": args, "kwargs": kwargs}

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def remove_job(self, job_id):
        self.jobs.pop(job_id, None)


def test_start_live_stream_resets_after_completed_dataset():
    old_scheduler = live_stream.scheduler
    old_state = dict(live_stream.live_stream_state)
    fake_scheduler = FakeScheduler()

    try:
        live_stream.set_scheduler(fake_scheduler)
        live_stream.live_stream_state.update({
            "running": False,
            "offset": 4800,
            "batches_ingested": 32,
            "last_result": {"inserted": 0, "skipped": 0, "complete": True},
            "last_error": "old error",
        })

        status = live_stream.start_live_stream(
            batch_size=150,
            interval_seconds=10,
            loop=False,
            reset=False,
            auto_ticket=True,
            ticket_every_batches=10,
            ticket_max_spikes=1,
        )

        assert status["running"] is True
        assert status["offset"] == 0
        assert status["batches_ingested"] == 0
        assert status["last_result"] is None
        assert status["last_error"] is None
        assert fake_scheduler.get_job("live_feedback_stream") is not None
    finally:
        live_stream.live_stream_state.clear()
        live_stream.live_stream_state.update(old_state)
        live_stream.set_scheduler(old_scheduler)


def test_completed_stream_schedules_final_ticket_detection():
    old_scheduler = live_stream.scheduler
    old_state = dict(live_stream.live_stream_state)
    fake_scheduler = FakeScheduler()

    try:
        live_stream.set_scheduler(fake_scheduler)
        live_stream.live_stream_state.update({
            "running": True,
            "offset": 0,
            "batch_size": 500,
            "loop": False,
            "auto_ticket": True,
            "ticket_every_batches": 10,
            "ticket_running": False,
            "batches_ingested": 0,
            "last_ticket_batch": None,
        })

        with patch.object(live_stream, "ingest_dataset", return_value={
            "success": True,
            "complete": True,
            "next_offset": 500,
        }):
            live_stream._live_stream_tick()

        assert live_stream.live_stream_state["running"] is False
        assert live_stream.live_stream_state["ticket_running"] is True
        assert fake_scheduler.get_job("auto_ticket_detection") is not None
    finally:
        live_stream.live_stream_state.clear()
        live_stream.live_stream_state.update(old_state)
        live_stream.set_scheduler(old_scheduler)


def test_live_stream_ticks_defer_llm_scoring_and_advance_consecutively():
    old_scheduler = live_stream.scheduler
    old_state = dict(live_stream.live_stream_state)
    fake_scheduler = FakeScheduler()

    try:
        live_stream.set_scheduler(fake_scheduler)
        live_stream.live_stream_state.update({
            "running": True,
            "offset": 0,
            "batch_size": 100,
            "loop": False,
            "auto_ticket": False,
            "ticket_every_batches": 2,
            "ticket_running": False,
            "batches_ingested": 0,
            "batch_running": False,
        })

        results = [
            {"success": True, "complete": False, "next_offset": offset, "inserted": 100}
            for offset in (100, 200, 300)
        ]
        with patch.object(live_stream, "ingest_dataset", side_effect=results) as ingest_mock:
            for _ in results:
                live_stream._live_stream_tick()

        assert [call.kwargs["offset"] for call in ingest_mock.call_args_list] == [0, 100, 200]
        assert all(
            call.kwargs["defer_llm_scoring"] is True
            for call in ingest_mock.call_args_list
        )
        assert live_stream.live_stream_state["batches_ingested"] == 3
        assert live_stream.live_stream_state["offset"] == 300
        assert live_stream.live_stream_state["batch_running"] is False
        assert live_stream.live_stream_state["last_batch_started_at"] is not None
        assert live_stream.live_stream_state["last_batch_completed_at"] is not None
    finally:
        live_stream.live_stream_state.clear()
        live_stream.live_stream_state.update(old_state)
        live_stream.set_scheduler(old_scheduler)


def test_manual_stop_schedules_detection_for_unprocessed_batches():
    old_scheduler = live_stream.scheduler
    old_state = dict(live_stream.live_stream_state)
    fake_scheduler = FakeScheduler()
    fake_scheduler.add_job(lambda: None, id="live_feedback_stream")

    try:
        live_stream.set_scheduler(fake_scheduler)
        live_stream.live_stream_state.update({
            "running": True,
            "auto_ticket": True,
            "ticket_running": False,
            "batches_ingested": 2,
            "last_ticket_batch": None,
        })

        status = live_stream.stop_live_stream()

        assert status["running"] is False
        assert status["ticket_running"] is True
        assert fake_scheduler.get_job("live_feedback_stream") is None
        assert fake_scheduler.get_job("auto_ticket_detection") is not None
    finally:
        live_stream.live_stream_state.clear()
        live_stream.live_stream_state.update(old_state)
        live_stream.set_scheduler(old_scheduler)


def test_manual_stop_defers_detection_when_batch_is_active():
    old_scheduler = live_stream.scheduler
    old_state = dict(live_stream.live_stream_state)
    fake_scheduler = FakeScheduler()

    try:
        live_stream.set_scheduler(fake_scheduler)
        live_stream.live_stream_state.update({
            "running": True,
            "auto_ticket": True,
            "ticket_running": False,
            "batches_ingested": 2,
            "last_ticket_batch": None,
            "final_detection_requested": False,
        })
        live_stream.live_stream_tick_lock.acquire()
        try:
            status = live_stream.stop_live_stream()
        finally:
            live_stream.live_stream_tick_lock.release()

        assert status["running"] is False
        assert status["ticket_running"] is False
        assert status["final_detection_requested"] is True
        assert live_stream.claim_final_detection_request() is True
    finally:
        if live_stream.live_stream_tick_lock.locked():
            live_stream.live_stream_tick_lock.release()
        live_stream.live_stream_state.clear()
        live_stream.live_stream_state.update(old_state)
        live_stream.set_scheduler(old_scheduler)
