"""Regression tests cho các lỗi tìm ra trong đợt phản biện 2026-08-27.

Mỗi test khoá đúng MỘT lỗi đã tồn tại thật trên nhánh main:

1. submit_feedback ghi cột `raw_text`/`cleaned_text` không tồn tại trong lược đồ
   `feedback`, và thiếu `user_id` (NOT NULL) -> công cụ duy nhất của tài khoản
   khách chưa bao giờ ghi được bản ghi nào; lỗi bị `except` nuốt thành chuỗi.
2. worker_ml khai INTERVAL=30 bằng os.getenv trong khi env_config khai 60
   -> tiến trình tốn LLM nhất chạy gấp đôi tần suất so với tài liệu.
3. orchestrator hard-code max_spikes=20 trong khi nguồn sự thật là
   DEFAULT_MAX_SPIKES (= số phòng ban).
"""
import inspect

import pytest

import agents.orchestrator as orch
from agent import chat_tools
from env_config import get_settings
from spike_detector import DEFAULT_MAX_SPIKES


# ── 1. Hợp đồng cột của submit_feedback ──────────────────────────────────────
FEEDBACK_COLUMNS = {
    "id", "user_id", "source", "channel", "text", "topic", "sentiment",
    "severity", "area", "confidence", "created_at",
    "needs_review", "reviewed", "overall_risk",
}


class _CaptureDB:
    def __init__(self):
        self.row = None

    def table(self, _name):
        return self

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        return type("R", (), {"data": [self.row]})()


def test_submit_feedback_only_writes_columns_that_exist(monkeypatch):
    db = _CaptureDB()
    monkeypatch.setattr(chat_tools, "get_supabase", lambda: db)
    out = chat_tools.submit_feedback("tài xế đi ẩu", user_id="u-1")
    assert "✅" in out
    unknown = set(db.row) - FEEDBACK_COLUMNS
    assert not unknown, f"ghi vào cột không có trong lược đồ: {unknown}"
    assert db.row["text"] == "tài xế đi ẩu"


def test_submit_feedback_refuses_when_user_id_missing(monkeypatch):
    db = _CaptureDB()
    monkeypatch.setattr(chat_tools, "get_supabase", lambda: db)
    out = chat_tools.submit_feedback("nội dung", user_id=None)
    assert db.row is None, "không được thử ghi khi thiếu user_id (cột NOT NULL)"
    assert "Không gửi được" in out


# ── 2. Mặc định cấu hình chỉ có một nguồn ────────────────────────────────────
def test_worker_ml_interval_comes_from_env_config():
    import worker_ml
    s = get_settings()
    assert worker_ml.INTERVAL == s.worker_ml_interval_seconds
    assert worker_ml.BATCH_SIZE == s.worker_ml_batch_size


def test_auto_ticket_workflow_defaults_off():
    """Alert chuyển trạng thái bằng nút ops, không tự động theo tuổi."""
    assert get_settings().auto_ticket_workflow_enabled is False


# ── 3. Trần điểm nóng lấy từ nguồn sự thật duy nhất ──────────────────────────
def test_orchestrator_does_not_hardcode_spike_cap():
    src = inspect.getsource(orch)
    assert "max_spikes=20" not in src, "trần bị hard-code, lệch khỏi DEFAULT_MAX_SPIKES"
    assert "DEFAULT_MAX_SPIKES" in src
    assert DEFAULT_MAX_SPIKES == 6


# ── 4. Tác tử phải ghi lại tool đã chạy (nếu không, không chứng minh được ép phạm vi) ──
def test_run_chat_agent_records_tools_used(monkeypatch):
    from agent import chat_agent

    calls = {"n": 0}

    def fake_completion(msgs, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"message": {"role": "assistant", "tool_calls": [
                {"id": "1", "function": {"name": "get_hot_areas", "arguments": "{}"}}]}}
        return {"content": "xong", "message": {"role": "assistant", "content": "xong"}}

    monkeypatch.setattr(chat_agent, "chat_completion", fake_completion)
    out = chat_agent.run_chat_agent(
        [{"role": "user", "content": "khu vực nào nóng nhất"}],
        scope_team="Vận hành",
        execute_fn=lambda name, args: "kết quả giả",
    )
    assert out["tools_used"] == [{"name": "get_hot_areas", "scope_team": "Vận hành"}]
