from main import _attach_task_titles


def test_enrich_completion_reports_adds_title():
    rows = [{"id": "c1", "task_id": "t1"}, {"id": "c2", "task_id": "t2"}]
    titles = {"t1": "Xử lý lỗi thanh toán", "t2": "Kiểm tra tài xế"}
    out = _attach_task_titles(rows, titles)
    assert out[0]["task_title"] == "Xử lý lỗi thanh toán"
    assert out[1]["task_title"] == "Kiểm tra tài xế"


def test_enrich_missing_title_falls_back_to_none():
    rows = [{"id": "c1", "task_id": "t1"}, {"id": "c2", "task_id": None}]
    titles = {"t1": "Có tiêu đề"}
    out = _attach_task_titles(rows, titles)
    assert out[0]["task_title"] == "Có tiêu đề"
    # task_id không có trong map -> None
    assert out[1]["task_title"] is None


def test_enrich_empty_rows_is_noop():
    assert _attach_task_titles([], {}) == []
