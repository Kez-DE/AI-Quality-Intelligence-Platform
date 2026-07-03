# Agent biết roster phòng ban — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bơm roster 6 phòng ban (từ hằng `DEPARTMENTS`) + đếm feedback per-phòng (admin) vào `DATA_CONTEXT` để agent trả lời được "có bao nhiêu phòng ban / phòng nào nóng nhất".

**Architecture:** Chỉ sửa `build_agent_data_context()` trong `pipeline/services/agent_context.py`. Roster đọc từ `DEPARTMENTS` (một nguồn sự thật). Guest đi nhánh khác (`GUEST_SYSTEM_PROMPT`) nên không ảnh hưởng — thêm test khẳng định.

**Tech Stack:** Python 3.12, pytest. Không thư viện mới.

**Spec:** `docs/superpowers/specs/2026-07-03-agent-department-roster-design.md`
**Nhánh:** `fix/agent-department-roster` (off main).

Đã xác minh: `build_agent_data_context` load `feedback` (300, chưa lọc khi admin) + đã import `route_ticket`, `Counter`; guest/public_only đi nhánh `GUEST_SYSTEM_PROMPT` (main.py:1172), không gọi hàm này.

---

## Task 1: Roster + đếm per-phòng trong build_agent_data_context (TDD)

**Files:**
- Modify: `pipeline/services/agent_context.py`
- Test: `pipeline/tests/test_agent_department_roster.py`

**Step 1: Viết test thất bại**

```python
"""build_agent_data_context phải chứa roster 6 phòng; admin có đếm per-phòng; guest không dính."""
import types
from services.agent_context import build_agent_data_context, GUEST_SYSTEM_PROMPT
from departments import DEPARTMENTS


def _user(role, department=None):
    return types.SimpleNamespace(role=role, department=department, id="u1", email="a@b.c")


def test_admin_context_has_full_roster():
    ctx = build_agent_data_context(_user("admin"))
    assert f"({len(DEPARTMENTS)})" in ctx or str(len(DEPARTMENTS)) in ctx
    for d in DEPARTMENTS:
        assert d in ctx, f"thiếu phòng {d} trong context admin"


def test_admin_context_has_per_department_feedback_line():
    ctx = build_agent_data_context(_user("admin"))
    assert "Feedback theo phòng" in ctx


def test_staff_with_dept_sees_roster_names_not_other_dept_counts():
    ctx = build_agent_data_context(_user("staff", "CSKH"))
    for d in DEPARTMENTS:
        assert d in ctx                       # roster tên: có
    assert "Feedback theo phòng" not in ctx   # đếm per-phòng: KHÔNG (chỉ admin)


def test_staff_without_dept_unchanged():
    ctx = build_agent_data_context(_user("staff", None))
    assert "chưa" in ctx.lower()              # giữ thông báo chưa có phạm vi


def test_guest_prompt_has_no_roster():
    for d in DEPARTMENTS:
        assert d not in GUEST_SYSTEM_PROMPT
```

**Step 2: Chạy test — xác nhận fail**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_agent_department_roster.py -q`
Expected: FAIL (roster/đếm chưa có).

> Lưu ý: 2 test đầu gọi Supabase thật (load feedback). Nếu env không có mạng/Supabase, hàm trả `DATA_CONTEXT_ERROR` và test roster vẫn cần chứa roster → đảm bảo roster được ghép TRƯỚC/NGOÀI phần phụ thuộc DB (xem Step 3: chèn roster kể cả nhánh lỗi DB). Nếu vẫn phụ thuộc DB, chạy với env `.env` đã có (repo có sẵn).

**Step 3: Sửa `build_agent_data_context`**

Thêm `DEPARTMENTS` vào import đầu file:
```python
from departments import alert_department, DEPARTMENTS
```

Trong `build_agent_data_context`, dựng roster + đếm per-phòng và chèn vào chuỗi trả về. Roster phải xuất hiện ở MỌI nhánh ops/admin (kể cả nhánh `DATA_CONTEXT_ERROR`), nên tính roster sớm:

```python
    # Roster phòng ban — nguồn sự thật DEPARTMENTS; luôn có trong context ops/admin.
    roster_line = f"- Phòng ban hệ thống ({len(DEPARTMENTS)}): {', '.join(DEPARTMENTS)}."
```
- Chèn `roster_line` vào chuỗi `DATA_CONTEXT` cuối cùng (sau dòng "Phạm vi dữ liệu").
- Ở nhánh `except ... DATA_CONTEXT_ERROR`: nối thêm `roster_line` để roster vẫn có dù DB lỗi.
- Chỉ khi `scope_team is None` (admin), tính đếm per-phòng từ feedback đã load:
```python
    per_dept_line = ""
    if scope_team is None:
        from collections import Counter as _C
        dept_counts = _C(
            route_ticket(f.get("topic", ""), f.get("severity", 3), f.get("sentiment"),
                         log_run=False)["team"]
            for f in feedback
        )
        if dept_counts:
            per_dept_line = "\n- Feedback theo phòng: " + ", ".join(
                f"{k}: {v}" for k, v in dept_counts.most_common())
```
- Nối `per_dept_line` vào chuỗi trả về (chỉ admin có).

**Step 4: Chạy test — pass**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_agent_department_roster.py -q`
Expected: PASS (5 test).

**Step 5: Không regress**

Run: `cd pipeline && .venv/bin/python -m pytest tests/ -q -k "agent or chat or context"`
Expected: PASS.

**Step 6: Commit**

```bash
git add pipeline/services/agent_context.py pipeline/tests/test_agent_department_roster.py
git commit -m "fix(agent): bơm roster 6 phòng + đếm per-phòng (admin) vào DATA_CONTEXT"
```

---

## Task 2: E2E thật + deploy + PR

**Step 1: E2E bằng JWT admin thật** (backend local port 8000 phải chạy; nếu chưa, bật `uvicorn main:app`):

```bash
cd pipeline
.venv/bin/python -c "
from env_config import get_settings
import httpx
s = get_settings(); key = s.supabase_publishable_key or s.vite_supabase_publishable_key
jwt = httpx.post(f'{s.supabase_url}/auth/v1/token?grant_type=password',
  headers={'apikey': key}, json={'email':'manhnguyn1912@gmail.com','password':'12345678'}, timeout=15).json()['access_token']
r = httpx.post('http://127.0.0.1:8000/api/agent/chat',
  headers={'Authorization': f'Bearer {jwt}'},
  json={'messages':[{'role':'user','content':'hiện tại có bao nhiêu phòng ban cụ thể'}]}, timeout=60)
print(r.json().get('content') or r.json())
"
```
Expected: trả lời nêu **6 phòng** + liệt kê đúng tên (IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận).

**Step 2: full suite**

Run: `cd pipeline && .venv/bin/python -m pytest -q`
Expected: xanh.

**Step 3: Push + PR**

```bash
git push -u origin fix/agent-department-roster
gh pr create --base main --title "fix(agent): admin chat biết roster 6 phòng ban" --body "<tóm tắt: nguyên nhân context thiếu roster, fix bơm DEPARTMENTS + đếm per-phòng admin, guest không dính; E2E verify>"
```

**Step 4:** Merge → GitHub Actions auto-deploy backend (pipeline/ đổi). Xác nhận deploy xong → hỏi lại trong app thấy trả đúng.

## Verify tổng
- 5 test Task 1 pass; full suite xanh.
- E2E admin hỏi "bao nhiêu phòng ban" → 6 + liệt kê.
- Guest/public không chứa roster (test + cấu trúc nhánh).
- Roster đọc từ `DEPARTMENTS` (đổi hằng → context đổi).
