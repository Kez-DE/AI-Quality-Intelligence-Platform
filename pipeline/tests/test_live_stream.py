import os
import sys

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
