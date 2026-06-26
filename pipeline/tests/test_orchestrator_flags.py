import inspect
from agents import orchestrator


def test_pipeline_accepts_phase_flags():
    sig = inspect.signature(orchestrator.run_agent_pipeline)
    assert "run_alert" in sig.parameters
    assert "run_report" in sig.parameters
    assert sig.parameters["run_alert"].default is True
    assert sig.parameters["run_report"].default is True
