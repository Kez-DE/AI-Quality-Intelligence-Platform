# AI Report Revamp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Tích hợp chọn lọc logic Báo cáo AI từ nhánh `docs` vào `main` (giữ 4 phòng ban), sửa lỗi tên task ở "Báo cáo hoàn thành", và dựng nội dung báo cáo theo 3 khối Vấn đề → Phân tích → Đề xuất.

**Architecture:** Backend Python (FastAPI + multi-agent trong `pipeline/`) sinh báo cáo qua `analyst_agent` → `report_builder` → bảng `department_reports`; frontend React (`app/`) đọc và hiển thị. Áp dụng thủ công từng hunk từ commit `d2d38f7`, loại trừ phần 4→6 phòng ban, file rác, refactor chat, migration trùng.

**Tech Stack:** Python 3.10+, FastAPI, pydantic, scikit-learn, Supabase (PostgreSQL), React 19 + TanStack Start + Vite, pytest.

**Spec:** `docs/superpowers/specs/2026-06-26-ai-report-revamp-design.md`

**Branch:** `feat/ai-report-revamp` (đã tạo, đang đứng trên nhánh này).

**Cách chạy test backend:** từ thư mục `pipeline/` (test import `from agents...`):
```bash
cd pipeline && python -m pytest tests/ -v
```
Nếu cần env: `set -a && source ../.env && set +a` trước khi chạy.

---

## Task 1: Schema — thêm 3 trường báo cáo (optional)

**Files:**
- Modify: `pipeline/agents/schemas.py:30-34` (class `AnalystAnalysis`)
- Test: `pipeline/tests/test_report_builder.py`

**Step 1: Viết test thất bại**

Thêm vào `pipeline/tests/test_report_builder.py`:
```python
def test_analyst_analysis_optional_new_fields():
    from agents.schemas import AnalystAnalysis
    # Thiếu các trường mới vẫn parse được (default rỗng)
    a = AnalystAnalysis(root_cause_summary="x", risk_level="LOW")
    assert a.prominent_theme is None
    assert a.feedback_summary == ""
    assert a.detailed_analysis == ""
    # Có trường mới thì giữ nguyên
    b = AnalystAnalysis(
        root_cause_summary="x", risk_level="LOW",
        prominent_theme="Sự cố hiệu năng App", feedback_summary="App treo",
        detailed_analysis="Phân tích chi tiết",
    )
    assert b.prominent_theme == "Sự cố hiệu năng App"
```

**Step 2: Chạy test để thấy fail**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py::test_analyst_analysis_optional_new_fields -v`
Expected: FAIL (`AnalystAnalysis` chưa có các trường mới / `feedback_summary` không tồn tại).

**Step 3: Sửa schema**

Trong `pipeline/agents/schemas.py`, đổi `AnalystAnalysis` thành:
```python
class AnalystAnalysis(BaseModel):
    prominent_theme: Optional[str] = None
    feedback_summary: str = ""
    detailed_analysis: str = ""
    root_cause_summary: str
    risk_level: str
    action_items: List[ActionItem] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
```
> Lưu ý: để `feedback_summary`/`detailed_analysis` **default `""`** (khác docs để
> required) nhằm tránh `ValidationError` khi LLM/mock trả thiếu trường.

**Step 4: Chạy lại test**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add pipeline/agents/schemas.py pipeline/tests/test_report_builder.py
git commit -m "feat(report): thêm prominent_theme/feedback_summary/detailed_analysis vào AnalystAnalysis"
```

---

## Task 2: analyst_agent — prompt + fallback (giữ Marketing)

**Files:**
- Modify: `pipeline/agents/analyst_agent.py` (prompt JSON block + `_fallback_analysis`)
- Test: `pipeline/tests/test_report_builder.py`

**Step 1: Viết test thất bại**

```python
def test_fallback_analysis_has_new_fields():
    from agents.analyst_agent import _fallback_analysis
    insights = {"top_topics": [{"topic": "App Issue", "count": 5}], "total_feedback": 5}
    out = _fallback_analysis("IT", insights)
    assert out["prominent_theme"]
    assert out["feedback_summary"]
    assert out["detailed_analysis"]
    assert out["root_cause_summary"]
```

**Step 2: Chạy test để thấy fail**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py::test_fallback_analysis_has_new_fields -v`
Expected: FAIL (KeyError các trường mới).

**Step 3: Cập nhật analyst_agent**

1. Trong `_fallback_analysis(...)`, tại lời gọi `AnalystAnalysis(...)`, thêm 3 trường (giống hunk docs):
```python
    analysis = AnalystAnalysis(
        prominent_theme=top_topic,
        feedback_summary=f"Hệ thống ghi nhận các phản hồi chủ yếu xoay quanh chủ đề {top_topic}.",
        detailed_analysis="Do hệ thống LLM gặp sự cố hoặc dữ liệu quá ít, phân tích chi tiết không khả dụng.",
        root_cause_summary=(
            f"Dữ liệu ghi nhận nhiều phản hồi liên quan đến {top_topic}; "
            "chưa đủ bằng chứng để khẳng định nguyên nhân gốc rễ và cần xác minh thêm."
        ),
        # ... giữ nguyên các tham số còn lại
```
2. Trong khối prompt (chuỗi hướng dẫn JSON), thêm đoạn yêu cầu tiêu đề trang trọng và 3 khoá JSON mới — **dán nguyên văn từ hunk docs** (phần "Trích xuất ĐÚNG BẢN CHẤT…" và 3 khoá `prominent_theme`/`feedback_summary`/`detailed_analysis` đứng trước `root_cause_summary`).
3. **KHÔNG** sửa `DEPARTMENT_PERSONAS`: giữ nguyên persona `"Marketing"`, không thêm `"Tài chính & Thanh toán"`, `"Sản phẩm"`, `"Quản lý Rủi ro & Gian lận"`.

Để lấy chính xác đoạn prompt cần dán:
```bash
git show origin/docs:pipeline/agents/analyst_agent.py | sed -n '160,180p'
```

**Step 4: Chạy lại test**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py -v`
Expected: PASS.

**Step 5: Xác minh không lẫn 6 phòng ban**

Run: `grep -n "Tài chính & Thanh toán\|Sản phẩm\|Rủi ro & Gian lận" pipeline/agents/analyst_agent.py`
Expected: **không có kết quả**. `grep -n '"Marketing"' pipeline/agents/analyst_agent.py` phải còn.

**Step 6: Commit**
```bash
git add pipeline/agents/analyst_agent.py pipeline/tests/test_report_builder.py
git commit -m "feat(report): prompt sinh tiêu đề trang trọng + 3 trường, giữ persona Marketing"
```

---

## Task 3: Migration — bỏ unique (team, report_date)

**Files:**
- Create: `supabase/migrations/20260629000000_remove_unique_department_reports.sql`

**Step 1: Tạo migration**

```sql
-- Cho phép nhiều báo cáo/ngày cho mỗi phòng: bỏ unique (team, report_date).
ALTER TABLE public.department_reports
  DROP CONSTRAINT IF EXISTS department_reports_team_date_unique;
```
> Timestamp `20260629000000` đặt **sau** `20260617143000_department_reports_unique.sql`
> (file tạo constraint) và sau `20260627000000`. Migration này phải áp **trước** khi
> code `insert` báo cáo thứ 2/ngày chạy.

**Step 2: Verify thứ tự migration**

Run: `ls supabase/migrations/ | sort | tail -6`
Expected: file mới đứng cuối danh sách sắp xếp.

**Step 3: Commit**
```bash
git add supabase/migrations/20260629000000_remove_unique_department_reports.sql
git commit -m "feat(db): bỏ unique (team, report_date) cho phép nhiều báo cáo/ngày"
```

---

## Task 4: report_builder.store — insert (nhiều báo cáo/ngày)

**Files:**
- Modify: `pipeline/agents/report_builder.py:184-225` (`store_department_report`)
- Test: `pipeline/tests/test_report_builder.py`

**Step 1: Viết test thất bại**

```python
def test_store_uses_insert_not_upsert():
    from agents.report_builder import store_department_report
    db = MagicMock()
    insert_mock = db.table.return_value.insert
    insert_mock.return_value.execute.return_value.data = [{"id": "r1"}]
    out = store_department_report(
        db, team="IT", report_date="2026-06-26", content="# x",
        suggested_tasks=[{"action": "a"}], root_cause_summary="rc",
    )
    assert out["stored"] is True
    insert_mock.assert_called_once()        # dùng insert
    db.table.return_value.upsert.assert_not_called()  # không upsert
```

**Step 2: Chạy test để thấy fail**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py::test_store_uses_insert_not_upsert -v`
Expected: FAIL (hiện đang dùng `upsert`, và còn truy vấn `select` approved-lock).

**Step 3: Sửa store_department_report**

Thay toàn bộ thân hàm (bỏ khối `existing = ...` và đổi `upsert`→`insert`):
```python
def store_department_report(
    db,
    *,
    team: str,
    report_date: str,
    content: str,
    suggested_tasks: list | None = None,
    root_cause_summary: str | None = None,
) -> dict[str, Any]:
    """Lưu một báo cáo mới. Cho phép nhiều báo cáo/ngày (không chặn bản đã duyệt)."""
    payload = {
        "team": team,
        "report_date": report_date,
        "content": content,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "suggested_tasks": suggested_tasks or [],
        "root_cause_summary": root_cause_summary,
    }
    result = db.table("department_reports").insert(payload).execute()
    return {"stored": True, "data": result.data or []}
```

**Step 4: Chạy lại test**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add pipeline/agents/report_builder.py pipeline/tests/test_report_builder.py
git commit -m "feat(report): lưu báo cáo bằng insert, cho phép nhiều báo cáo/ngày"
```

---

## Task 5: report_builder.markdown — 3 khối + tiêu đề

**Files:**
- Modify: `pipeline/agents/report_builder.py` (`build_department_report_markdown`)
- Test: `pipeline/tests/test_report_builder.py`

**Step 1: Viết test thất bại**

```python
def test_markdown_has_three_sections_and_title():
    from agents.report_builder import build_department_report_markdown
    analysis_result = {"status": "success", "analysis": {
        "prominent_theme": "Sự cố hiệu năng App",
        "feedback_summary": "Khách báo app treo khi đặt xe.",
        "detailed_analysis": "Tần suất tăng ở khung giờ cao điểm.",
        "root_cause_summary": "Nghi do tải máy chủ.",
        "risk_level": "HIGH",
        "action_items": [{"action": "Rà soát server", "priority": "P2", "deadline": "48h"}],
        "evidence": ["App Issue: 12/20"],
    }}
    md = build_department_report_markdown("IT", _insights(), analysis_result)
    assert md.startswith("# Báo cáo Vận hành - Phòng IT: Sự cố hiệu năng App")
    assert "## Vấn đề ghi nhận" in md
    assert "Khách báo app treo" in md
    assert "## Phân tích & nguyên nhân" in md
    assert "## Đề xuất giải quyết" in md
    assert "Rà soát server" in md
```

**Step 2: Chạy test để thấy fail**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py::test_markdown_has_three_sections_and_title -v`
Expected: FAIL.

**Step 3: Sửa build_department_report_markdown**

3a. Trước khi tạo `lines`, tính tiêu đề:
```python
    top_topics = insights.get("top_topics") or []
    prominent_theme = str(analysis.get("prominent_theme") or "").strip()
    feedback_summary = str(analysis.get("feedback_summary") or "").strip()
    detailed_analysis = str(analysis.get("detailed_analysis") or "").strip()
    topic_suffix = ""
    if prominent_theme:
        topic_suffix = f": {prominent_theme}"
    elif top_topics:
        topic_suffix = f": {' / '.join(_cell(t.get('topic')) for t in top_topics[:2])}"
```
> Bỏ dòng `top_topics = insights.get("top_topics") or []` cũ ở giữa hàm (đã khai báo ở trên).

3b. Đổi dòng tiêu đề đầu `lines`:
```python
        f"# Báo cáo Vận hành - Phòng {_cell(team)}{topic_suffix}",
```

3c. Ngay sau khối "## Tóm tắt điều hành" (bảng KPI) — hoặc trước "## Vấn đề nổi bật" — chèn 3 khối mới:
```python
    lines.extend([
        "",
        "## Vấn đề ghi nhận",
        "",
        _cell(feedback_summary) if feedback_summary else "Chưa có tóm tắt vấn đề từ AI.",
    ])
```
Khối "Phân tích & nguyên nhân" thay cho mục "## Nhận định AI cần xác minh" hiện tại — đổi tiêu đề và thêm detailed_analysis + risk + bằng chứng:
```python
    root_cause = analysis.get("root_cause_summary") or "Chưa đủ mẫu phản hồi để đưa ra nhận định nguyên nhân."
    lines.extend([
        "",
        "## Phân tích & nguyên nhân",
        "",
        _cell(detailed_analysis) if detailed_analysis else "Chưa có phân tích chi tiết.",
        "",
        f"**Nguyên nhân (cần xác minh):** {_cell(root_cause)}",
        f"**Mức rủi ro:** {_cell(risk_level)}",
        "",
        "### Bằng chứng từ dữ liệu",
        "",
    ])
    # ... giữ phần dựng `evidence` hiện có
```
Đổi tiêu đề "## Kế hoạch cải tiến" → "## Đề xuất giải quyết" (giữ nguyên bảng action items bên dưới).

> Giữ các bảng "Vấn đề nổi bật" (top topics), "Khu vực cần chú ý", "Dự báo và theo dõi", "Phạm vi và độ tin cậy" như cũ — chỉ thêm 3 khối nội dung và đổi 2 tiêu đề.

**Step 4: Chạy lại test**

Run: `cd pipeline && python -m pytest tests/test_report_builder.py -v`
Expected: PASS (cả test cũ vẫn xanh).

**Step 5: Commit**
```bash
git add pipeline/agents/report_builder.py pipeline/tests/test_report_builder.py
git commit -m "feat(report): body 3 khối Vấn đề/Phân tích/Đề xuất + tiêu đề prominent_theme"
```

---

## Task 6: task_agent — truyền suggested_tasks + root_cause

**Files:**
- Modify: `pipeline/agents/task_agent.py` (`generate_daily_report`, lời gọi `store_department_report`)
- Test: `pipeline/tests/test_report_approval.py` (lấy từ docs, chỉnh 4 phòng ban)

**Step 1: Lấy test từ docs và rà soát phòng ban**

```bash
git show origin/docs:pipeline/tests/test_report_approval.py > pipeline/tests/test_report_approval.py
grep -n "Tài chính\|Sản phẩm\|Rủi ro\|Marketing\|IT\|CSKH\|Vận hành" pipeline/tests/test_report_approval.py
```
Sửa mọi tham chiếu phòng ban 6-dept (nếu có) về 4 phòng `IT/CSKH/Vận hành/Marketing`.

**Step 2: Chạy test để thấy fail**

Run: `cd pipeline && python -m pytest tests/test_report_approval.py -v`
Expected: FAIL (task_agent chưa truyền `suggested_tasks`/`root_cause_summary`).

**Step 3: Sửa task_agent.generate_daily_report**

Tại lời gọi `store_department_report(...)` thêm:
```python
        analysis_dict = analysis.get("analysis") or {}
        stored = store_department_report(
            db,
            team=team,
            report_date=datetime.utcnow().date().isoformat(),
            content=content,
            suggested_tasks=analysis_dict.get("action_items", []),
            root_cause_summary=analysis_dict.get("root_cause_summary", ""),
        )
```

**Step 4: Chạy lại test**

Run: `cd pipeline && python -m pytest tests/test_report_approval.py tests/test_report_builder.py -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add pipeline/agents/task_agent.py pipeline/tests/test_report_approval.py
git commit -m "feat(report): task_agent lưu suggested_tasks + root_cause vào báo cáo"
```

---

## Task 7: orchestrator — cờ run_alert / run_report

**Files:**
- Modify: `pipeline/agents/orchestrator.py` (`run_agent_pipeline`, `run_full_cycle`)
- Test: `pipeline/tests/test_orchestrator_flags.py` (tạo mới)

**Step 1: Viết test thất bại**

```python
# pipeline/tests/test_orchestrator_flags.py
import inspect
from agents import orchestrator

def test_pipeline_accepts_phase_flags():
    sig = inspect.signature(orchestrator.run_agent_pipeline)
    assert "run_alert" in sig.parameters
    assert "run_report" in sig.parameters
```

**Step 2: Chạy test để thấy fail**

Run: `cd pipeline && python -m pytest tests/test_orchestrator_flags.py -v`
Expected: FAIL.

**Step 3: Áp hunk orchestrator từ docs**

Áp đúng diff docs cho `orchestrator.py`: thêm tham số `run_alert: bool = True, run_report: bool = True`, và gating các phase alert/task/SLA bằng `run_alert`, phase insight/analyst bằng `run_report`; `run_full_cycle` gọi với cả hai `True`. Tham chiếu:
```bash
git show origin/docs:pipeline/agents/orchestrator.py | sed -n '40,120p'
```

**Step 4: Chạy lại test**

Run: `cd pipeline && python -m pytest tests/test_orchestrator_flags.py -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add pipeline/agents/orchestrator.py pipeline/tests/test_orchestrator_flags.py
git commit -m "feat(agent): orchestrator tách phase alert/report bằng cờ run_alert/run_report"
```

---

## Task 8: worker_agent — tách lịch alert / report

**Files:**
- Modify: `pipeline/worker_agent.py`

**Step 1: Áp hunk worker_agent từ docs**

Áp đúng diff docs: tách `run_pipeline` thành `run_alert_pipeline` (gọi `run_agent_pipeline(hours=1, run_alert=True, run_report=False)`) và `run_report_pipeline` (`hours=HOURS, run_alert=False, run_report=True`); scheduler chạy alert mỗi `INTERVAL`, report cron `hour="9,14"`. Tham chiếu:
```bash
git show origin/docs:pipeline/worker_agent.py
```

**Step 2: Verify import/khởi động (smoke)**

Run: `cd pipeline && python -c "import worker_agent; print('worker_agent OK')"`
Expected: in `worker_agent OK` (không lỗi import).

**Step 3: Commit**
```bash
git add pipeline/worker_agent.py
git commit -m "feat(worker): alert mỗi chu kỳ (1h) + report theo lịch 09:00/14:00"
```

---

## Task 9: Backend — completion-reports kèm task_title (ask B)

**Files:**
- Modify: `pipeline/main.py` (`list_completion_reports` ~815, `list_task_completion_reports` ~777)
- Test: `pipeline/tests/test_completion_report_title.py` (tạo mới)

**Step 1: Viết test thất bại**

Test hàm enrich thuần (tách logic để dễ test):
```python
# pipeline/tests/test_completion_report_title.py
def test_enrich_completion_reports_adds_title():
    from main import _attach_task_titles
    rows = [{"id": "c1", "task_id": "t1"}, {"id": "c2", "task_id": "t2"}]
    titles = {"t1": "Xử lý lỗi thanh toán", "t2": "Kiểm tra tài xế"}
    out = _attach_task_titles(rows, titles)
    assert out[0]["task_title"] == "Xử lý lỗi thanh toán"
    assert out[1]["task_title"] == "Kiểm tra tài xế"
```

**Step 2: Chạy test để thấy fail**

Run: `cd pipeline && python -m pytest tests/test_completion_report_title.py -v`
Expected: FAIL (`_attach_task_titles` chưa tồn tại).

**Step 3: Thêm helper + dùng trong endpoint**

Thêm helper thuần trong `pipeline/main.py`:
```python
def _attach_task_titles(rows: list[dict], titles: dict[str, str]) -> list[dict]:
    for r in rows:
        r["task_title"] = titles.get(r.get("task_id")) or None
    return rows
```
Trong `list_completion_reports` (và `list_task_completion_reports`), sau khi có `data`, nạp title theo `task_id`:
```python
        task_ids = list({r.get("task_id") for r in data if r.get("task_id")})
        titles = {}
        if task_ids:
            trows = db.table("tasks").select("id,title").in_("id", task_ids).execute().data or []
            titles = {t["id"]: t.get("title") for t in trows}
        data = _attach_task_titles(data, titles)
```

**Step 4: Chạy lại test**

Run: `cd pipeline && python -m pytest tests/test_completion_report_title.py -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add pipeline/main.py pipeline/tests/test_completion_report_title.py
git commit -m "feat(api): completion-reports trả kèm task_title"
```

---

## Task 10: Frontend — hiển thị tên task ở "Báo cáo hoàn thành"

**Files:**
- Modify: `app/src/routes/_authenticated/completion-reports.tsx:20-31` (type) và phần render thẻ (~184-210)

**Step 1: Thêm field vào type**

Trong type `CompletionReport`, thêm:
```ts
  task_title?: string | null;
```

**Step 2: Render tiêu đề task trong thẻ**

Ngay trên dòng badge đầu thẻ (trước `<div className="flex items-center gap-2 flex-wrap">`), thêm:
```tsx
                <h3 className="font-bold text-sm text-xanh-deep">
                  {r.task_title || "Task không xác định"}
                </h3>
```

**Step 3: Typecheck/build frontend**

Run: `cd app && npx tsc --noEmit`
Expected: không lỗi type liên quan file này. (Nếu repo dùng `npm run build` để typecheck, dùng lệnh đó.)

**Step 4: Commit**
```bash
git add app/src/routes/_authenticated/completion-reports.tsx
git commit -m "feat(ui): hiển thị tên task trong trang Báo cáo hoàn thành"
```

---

## Task 11: Frontend — reports.tsx tiêu đề + thời gian

**Files:**
- Modify: `app/src/routes/_authenticated/reports.tsx:368-400`
- Modify: type `Report` (tìm nơi khai báo) — thêm `created_at`

**Step 1: Tìm type Report**

Run: `grep -rn "report_date\|type Report\|content:" app/src/routes/_authenticated/reports.tsx | head`
Mở chỗ khai báo type báo cáo dùng trong trang; thêm field:
```ts
  created_at: string;
```

**Step 2: Áp hunk reports.tsx từ docs**

Áp đúng diff docs cho `reports.tsx`: thêm `firstLine`/`reportTitle` từ dòng đầu `content`, render `{reportTitle}`, và đổi ngày sang `report.created_at` (`toLocaleString` short/short). Tham chiếu:
```bash
git show origin/docs:app/src/routes/_authenticated/reports.tsx | sed -n '360,405p'
```

**Step 3: Typecheck**

Run: `cd app && npx tsc --noEmit`
Expected: không lỗi.

**Step 4: Commit**
```bash
git add app/src/routes/_authenticated/reports.tsx
git commit -m "feat(ui): tiêu đề báo cáo lấy từ nội dung + hiển thị thời gian tạo"
```

---

## Task 12: Tài liệu cơ chế (co_che.md) + README

**Files:**
- Modify: `docs/project/co_che.md` (mục cơ chế báo cáo)
- Modify: `README.md` (dòng tính năng báo cáo, nếu cần)

**Step 1: So sánh nội dung báo cáo từ docs**

```bash
git show origin/docs:co_che.md > /tmp/co_che_docs.md
diff <(sed -n '1,200p' /tmp/co_che_docs.md) <(sed -n '1,200p' docs/project/co_che.md) | head -80
```

**Step 2: Gộp mô tả cơ chế mới**

Trong `docs/project/co_che.md`, cập nhật phần báo cáo để phản ánh: nhiều báo cáo/ngày, lịch 09:00 & 14:00, nội dung 3 khối Vấn đề/Phân tích/Đề xuất, và liên kết báo cáo→task. **Giữ 4 phòng ban**; KHÔNG tạo lại file ở root.

**Step 3: Commit**
```bash
git add docs/project/co_che.md README.md
git commit -m "docs: cập nhật cơ chế Báo cáo AI (nhiều báo cáo/ngày, lịch, 3 khối)"
```

---

## Task 13: Verify toàn bộ + áp migration + bàn giao

**Step 1: Chạy toàn bộ test backend**

Run: `cd pipeline && python -m pytest tests/ -v`
Expected: tất cả PASS.

**Step 2: Typecheck/build frontend**

Run: `cd app && npx tsc --noEmit` (hoặc `npm run build`)
Expected: không lỗi.

**Step 3: Áp migration lên Supabase (gotcha đã biết)**

Áp các migration đang chờ — gồm `20260627000000_suggested_tasks_and_report_link.sql`
và `20260629000000_remove_unique_department_reports.sql` — lên Supabase remote
(qua quy trình migration của dự án; xem `docs/project/setup-supabase.md`).
> Bắt buộc: drop-unique phải áp trước khi worker sinh báo cáo thứ 2/ngày.

**Step 4: Smoke luồng báo cáo (thủ công, tùy chọn)**

Chạy backend + frontend local, tạo báo cáo mới ở `/reports`, kiểm tra tiêu đề +
3 khối; mở `/completion-reports` kiểm tra hiển thị tên task.

**Step 5: Xác nhận không lẫn 6 phòng ban**

Run:
```bash
git diff main...feat/ai-report-revamp --name-only | grep -E "departments.py|routing_table.json|DepartmentBadge|insights.tsx" || echo "OK - khong dung file phong ban"
grep -rn "Tài chính & Thanh toán\|Quản lý Rủi ro" pipeline/ app/src/ || echo "OK - khong co 6 phong ban"
```
Expected: cả hai in "OK".

**Step 6: PR + merge + pull về local (khi người dùng yêu cầu)**

```bash
git push -u origin feat/ai-report-revamp
gh pr create --base main --title "Nâng cấp Báo cáo AI (giữ 4 phòng ban)" --body "Xem docs/superpowers/specs/2026-06-26-ai-report-revamp-design.md"
# sau khi merge:
git checkout main && git pull
```

---

## Thứ tự thực thi & phụ thuộc

1 → 2 (schema trước prompt) → 3 (migration drop unique) → 4 (insert) → 5 (markdown)
→ 6 (task_agent) → 7 (orchestrator) → 8 (worker) → 9,10 (ask B) → 11 (reports UI)
→ 12 (docs) → 13 (verify/bàn giao). Task 9 và 10 độc lập với phần báo cáo, có thể làm song song.

## Lưu ý DRY/YAGNI/TDD
- Mỗi task có test trước khi sửa code (trừ task UI/worker dùng typecheck/smoke).
- Không động vào file phòng ban, `chat.tsx`, `scratch/*`, file docs ở root.
- Commit nhỏ theo từng task.
