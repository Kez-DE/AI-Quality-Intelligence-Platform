from unittest.mock import MagicMock, patch

import worker_agent


def test_agent_worker_runs_pipeline_immediately_on_start():
    scheduler = MagicMock()

    with patch.object(worker_agent, "BackgroundScheduler", return_value=scheduler):
        configured = worker_agent.build_scheduler()

    assert configured is scheduler
    kwargs = scheduler.add_job.call_args.kwargs
    assert kwargs["id"] == "agent_pipeline"
    assert kwargs["next_run_time"] is not None
