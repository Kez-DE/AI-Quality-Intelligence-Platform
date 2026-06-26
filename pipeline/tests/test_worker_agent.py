from unittest.mock import MagicMock, patch

import worker_agent


def test_agent_worker_runs_pipeline_immediately_on_start():
    scheduler = MagicMock()

    with patch.object(worker_agent, "BackgroundScheduler", return_value=scheduler):
        configured = worker_agent.build_scheduler()

    assert configured is scheduler

    jobs_by_id = {
        call.kwargs["id"]: call.kwargs for call in scheduler.add_job.call_args_list
    }

    # Alert pipeline runs on an interval and fires immediately on start.
    assert "alert_pipeline" in jobs_by_id
    assert jobs_by_id["alert_pipeline"]["next_run_time"] is not None

    # Report pipeline runs on a daily cron (09:00, 14:00).
    assert "report_pipeline" in jobs_by_id
    assert jobs_by_id["report_pipeline"]["hour"] == "9,14"
