"""rescore_overall_risk must not fabricate P1 for sentinel-0 (unscored) rows."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import rescore_overall_risk as rescore


def _run(rows):
    with patch.object(rescore, "_fetch_all", return_value=rows):
        return rescore.rescore_feedback(MagicMock(), apply=False)


def test_sentinel_zero_rows_are_skipped():
    """worker_ml writes overall_risk=0 for LLM-failed rows ('attempted, needs
    human'). Rescore treating 0 as 'already scored' would compute
    calculate_overall_risk(0,...)=1 and stamp a fabricated verified-P1."""
    result = _run([{
        "id": "f1", "sentiment": "negative", "severity": "P3", "overall_risk": 0,
        "risk_safety": 0, "risk_fraud": 0, "risk_attitude": 0,
        "risk_vehicle": 0, "risk_compliance": 0,
    }])
    assert result["changed"] == 0


def test_scored_rows_still_rescored():
    result = _run([{
        "id": "f2", "sentiment": "negative", "severity": "P1", "overall_risk": 4,
        "risk_safety": 8, "risk_fraud": 0, "risk_attitude": 0,
        "risk_vehicle": 0, "risk_compliance": 0,
    }])
    assert result["changed"] == 1
