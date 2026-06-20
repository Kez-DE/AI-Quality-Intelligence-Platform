from unittest.mock import MagicMock, patch

from ingest import _process_and_insert_batch


def test_deferred_batch_skips_llm_and_inserts_for_ml_worker():
    db = MagicMock()
    payload = [{
        "text": "Phản hồi tiêu cực",
        "sentiment": "negative",
        "severity": "P3",
    }]

    with patch("agents.scoring_agent.score_feedback_batch") as score_batch:
        _process_and_insert_batch(db, payload, defer_llm_scoring=True)

    score_batch.assert_not_called()
    db.table.assert_called_once_with("feedback")
    db.table.return_value.insert.assert_called_once_with(payload)
