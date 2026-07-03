# MCP Server + Dev-env + KB 6 phòng ban — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose 6 tool nghiệp vụ sẵn có thành một MCP server (stdio) để agent ngoài truy vấn được platform, đồng thời sửa dev-env Python và bổ sung KB cho 3 phòng ban còn thiếu.

**Architecture:** MCP server là adapter mỏng bọc `pipeline/agent/chat_tools.py` — không sửa file đó. Danh tính (role + phòng ban) cố định phía server qua env, không lấy từ caller; mọi tool gọi qua `execute_tool(..., scope_team=<env>)` nên client không thể leo quyền. KB dùng 2 lớp: keyword load `.md` lúc runtime, vector cần chạy lại `seed_graph_kb.py`.

**Tech Stack:** Python 3.11/3.12, `mcp` SDK (FastMCP, stdio), pytest, Supabase (service role), Cohere embeddings.

**Spec:** `docs/superpowers/specs/2026-07-02-mcp-server-and-improvements-design.md`

---

## Task 0: Sửa dev-env Python (làm trước — mở khóa vòng test)

Phải làm đầu tiên: full `pytest` đang crash trên Python 3.14, các task sau cần suite chạy sạch.

**Files:**
- Modify: `pipeline/.venv` (tạo lại, không track)
- Modify: `README.md` (ghi pin Python)

**Step 1: Xác nhận có Python 3.11 hoặc 3.12**

Run: `python3.12 --version || python3.11 --version`
Expected: in ra `Python 3.12.x` hoặc `3.11.x`. Nếu không có, cài qua `brew install python@3.12`.

**Step 2: Tạo lại venv khớp production (Docker = 3.11-slim)**

```bash
cd pipeline
rm -rf .venv
python3.12 -m venv .venv   # hoặc python3.11
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

**Step 3: Chạy full suite, xác nhận không còn crash teardown**

Run: `cd pipeline && .venv/bin/python -m pytest -q`
Expected: PASS — in ra dòng tổng kết kiểu `68 passed, 3 skipped` (không còn `ValueError: I/O operation on closed file`).

**Step 4: Ghi pin Python vào README**

Trong `README.md` mục "Yêu cầu", đổi `Python 3.10+` thành ghi rõ khớp production:
```
- Python 3.11 hoặc 3.12 (production Docker pin 3.11-slim; tránh 3.14 — pytest crash teardown)
```

**Step 5: Commit**

```bash
git add README.md
git commit -m "fix(dev): pin Python 3.11/3.12 cho venv, tránh pytest crash trên 3.14"
```

---

## Task 1: KB cho 3 phòng ban còn thiếu

**Files:**
- Create: `data/knowledge_base/sop/sop_tai_chinh_thanh_toan.md`
- Create: `data/knowledge_base/sop/sop_san_pham.md`
- Create: `data/knowledge_base/sop/sop_rui_ro_gian_lan.md`
- Test: `pipeline/tests/test_kb_six_departments.py`

**Step 1: Viết test thất bại**

```python
# pipeline/tests/test_kb_six_departments.py
from agent.knowledge_base import search_knowledge

NEW_DEPTS = ["Tài chính & Thanh toán", "Sản phẩm", "Quản lý Rủi ro & Gian lận"]

def test_each_new_department_has_kb_docs():
    for dept in NEW_DEPTS:
        results = search_knowledge("quy trình xử lý", department=dept, top_k=3)
        assert results, f"KB rỗng cho phòng {dept}"
        # chunk phải đúng phòng đã lọc
        assert any((r.get("department") or "") == dept for r in results), \
            f"Không có chunk gắn đúng department={dept}"
```

**Step 2: Chạy test, xác nhận fail**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_kb_six_departments.py -q`
Expected: FAIL — KB rỗng cho phòng mới.

**Step 3: Soạn 3 file KB**

Mỗi file bắt đầu bằng YAML frontmatter, `department` khớp CHÍNH XÁC tên phòng chuẩn (kiểm tra chính tả trong `pipeline/departments.py` trước khi viết). Chia nội dung theo heading `##` (mỗi `##` = một chunk). Mẫu cho `sop_tai_chinh_thanh_toan.md`:

```markdown
---
department: "Tài chính & Thanh toán"
category: sop
severity_scope: [P2, P3, P4]
tags: [thanh toán, hoàn tiền, đối soát, hóa đơn, ví điện tử]
---

# SOP — Tài chính & Thanh toán

## Xử lý khiếu nại trừ tiền sai / trừ 2 lần
Bước 1: xác minh giao dịch trên cổng thanh toán...
(nội dung nghiệp vụ thật, 1–3 đoạn)

## Quy trình hoàn tiền
...

## Đối soát chênh lệch cước và ví điện tử
...
```

Làm tương tự cho `sop_san_pham.md` (department `"Sản phẩm"`: lỗi tính năng app, phản hồi tính năng, backlog sản phẩm) và `sop_rui_ro_gian_lan.md` (department `"Quản lý Rủi ro & Gian lận"`: phát hiện gian lận cước, tài khoản giả, chống lạm dụng khuyến mãi).

**Step 4: Chạy test keyword layer, xác nhận pass**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_kb_six_departments.py -q`
Expected: PASS (keyword layer load `.md` lúc runtime, không cần index).

**Step 5: Re-seed lớp vector (graph_nodes) cho hybrid search**

Cần Supabase + Cohere env trong `.env`. Chạy:
```bash
cd pipeline && .venv/bin/python seed_graph_kb.py
```
Expected: in tiến trình "Xóa đồ thị cũ..." → chèn nodes/edges, không lỗi. Nếu thiếu key Cohere/Supabase, ghi lại và để reviewer chạy khi có env (test keyword đã bảo vệ phần logic).

**Step 6: Kiểm tra hybrid không hỏng KB cũ**

Run: `cd pipeline && .venv/bin/python -m pytest tests/ -q -k "knowledge or rag or chat_tools"`
Expected: PASS — query phòng legacy vẫn ra kết quả.

**Step 7: Commit**

```bash
git add data/knowledge_base/sop/sop_tai_chinh_thanh_toan.md data/knowledge_base/sop/sop_san_pham.md data/knowledge_base/sop/sop_rui_ro_gian_lan.md pipeline/tests/test_kb_six_departments.py
git commit -m "feat(kb): thêm SOP cho Tài chính/Sản phẩm/Rủi ro&Gian lận — phủ đủ 6 phòng"
```

---

## Task 2: Decision record cho MCP server (hard gate)

**Files:**
- Create: `docs/harness/decisions/NNNN-mcp-server-expose-platform.md` (dùng số kế tiếp; xem `ls docs/harness/decisions/`)

**Step 1: Viết decision từ template**

Copy `docs/harness/templates/decision.md`, điền: quyết định expose platform qua MCP stdio server, identity cố định server-side (env `MCP_ROLE`/`MCP_SCOPE_TEAM`), lý do chọn hướng A (tái dùng `chat_tools.py`, không rewrite), ranh giới bảo mật (scope_team không đọc từ caller), phần out-of-scope (HTTP đa tenant).

**Step 2: Đăng ký row durable**

Run: `./scripts/bin/harness-cli decision add` (theo cú pháp help của CLI).
Expected: decision xuất hiện khi `./scripts/bin/harness-cli query decisions` (hoặc lệnh liệt kê tương ứng).

**Step 3: Commit**

```bash
git add docs/harness/decisions/
git commit -m "docs(decision): MCP server expose platform — identity server-side, hướng A"
```

---

## Task 3: Thêm dependency `mcp`

**Files:**
- Modify: `pipeline/requirements.txt`

**Step 1: Thêm dòng dependency**

Thêm vào `pipeline/requirements.txt`:
```
mcp>=1.28.0
```

**Step 2: Cài**

Run: `cd pipeline && .venv/bin/pip install -r requirements.txt`
Expected: `mcp` cài thành công.

**Step 3: Xác nhận import được**

Run: `cd pipeline && .venv/bin/python -c "from mcp.server.fastmcp import FastMCP; print('ok')"`
Expected: in `ok`.

**Step 4: Commit**

```bash
git add pipeline/requirements.txt
git commit -m "build(pipeline): thêm dependency mcp (FastMCP) cho MCP server"
```

---

## Task 4: Lõi routing — helper chọn tool theo role + wrapper ép scope

Tách phần logic thuần (testable không cần stdio) khỏi phần transport.

**Files:**
- Create: `pipeline/mcp_server.py`
- Test: `pipeline/tests/test_mcp_server.py`

**Step 1: Viết test thất bại — role filtering + escalation guard**

```python
# pipeline/tests/test_mcp_server.py
import mcp_server as m

def test_staff_role_excludes_manager_tools():
    names = set(m.registered_tool_names("staff"))
    assert "search_knowledge_base" in names
    assert "get_team_priority_tasks" in names
    assert "get_feedback_summary" not in names   # tool cấp điều hành
    assert "get_hot_areas" not in names

def test_guest_role_only_submit_feedback():
    assert m.registered_tool_names("guest") == ["submit_feedback"]

def test_admin_role_has_all_ops_tools():
    names = set(m.registered_tool_names("admin"))
    assert {"get_feedback_summary", "get_hot_areas", "get_sla_tickets",
            "get_team_priority_tasks", "search_knowledge_base"} <= names

def test_scope_team_cannot_be_overridden_by_args(monkeypatch):
    captured = {}
    def fake_execute(name, args, scope_team=None, sources_out=None):
        captured["scope_team"] = scope_team
        return "ok"
    monkeypatch.setattr(m, "execute_tool", fake_execute)
    # client cố tình truyền scope_team/team_name khác trong args
    m.call_tool(role="staff", scope_team="CSKH",
                name="get_team_priority_tasks", args={"team_name": "Safety"})
    assert captured["scope_team"] == "CSKH"   # bị ép về phòng của server, không nghe args
```

**Step 2: Chạy test, xác nhận fail**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_mcp_server.py -q`
Expected: FAIL — `mcp_server` chưa có `registered_tool_names`/`call_tool`.

**Step 3: Viết lõi trong `pipeline/mcp_server.py`**

```python
"""MCP server (stdio) expose 6 tool nghiệp vụ ra ngoài.

Danh tính cố định phía server qua env — client KHÔNG truyền được:
  MCP_ROLE       admin | manager | staff | guest
  MCP_SCOPE_TEAM tên phòng ban (rỗng = toàn hệ thống, chỉ hợp lệ khi admin)

Adapter mỏng: không sửa agent/chat_tools.py, chỉ gọi vào.
"""
import os

from agent.chat_tools import (
    tools_for_role,
    execute_tool,
    execute_guest_tool,
    GUEST_TOOLS_DEFINITIONS,
)


def registered_tool_names(role: str | None) -> list[str]:
    """Tên các tool role này được thấy. guest = chỉ submit_feedback."""
    if role == "guest":
        return [t["function"]["name"] for t in GUEST_TOOLS_DEFINITIONS]
    return [t["function"]["name"] for t in tools_for_role(role)]


def call_tool(role: str | None, scope_team: str | None, name: str, args: dict) -> str:
    """Route tool call. scope_team LUÔN từ config server, không bao giờ từ args."""
    if role == "guest":
        return execute_guest_tool(name, args, user_id=None)
    # admin: scope_team=None (toàn hệ thống). ops: ép về phòng của server.
    effective_scope = None if role == "admin" else scope_team
    return execute_tool(name, args, scope_team=effective_scope)
```

**Step 4: Chạy test, xác nhận pass**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_mcp_server.py -q`
Expected: PASS (4 test).

**Step 5: Commit**

```bash
git add pipeline/mcp_server.py pipeline/tests/test_mcp_server.py
git commit -m "feat(mcp): lõi routing — role filtering + ép scope_team server-side"
```

---

## Task 5: Wiring FastMCP + entrypoint stdio

**Files:**
- Modify: `pipeline/mcp_server.py`

**Step 1: Thêm builder + entrypoint (dưới phần lõi Task 4)**

```python
from mcp.server.fastmcp import FastMCP


def build_server() -> FastMCP:
    role = os.environ.get("MCP_ROLE", "guest").strip().lower()
    scope_team = os.environ.get("MCP_SCOPE_TEAM", "").strip() or None
    if role != "admin" and scope_team is None and role != "guest":
        raise SystemExit("MCP_SCOPE_TEAM bắt buộc khi role ops (staff/manager)")

    server = FastMCP("xanhsm-quality")

    for tool_name in registered_tool_names(role):
        def _make(tn: str):
            def _handler(**kwargs) -> str:
                return call_tool(role, scope_team, tn, kwargs)
            _handler.__name__ = tn
            return _handler
        # mô tả lấy từ definition gốc để client hiểu tool
        server.add_tool(_make(tool_name), name=tool_name,
                        description=_description_for(tool_name, role))
    return server


def _description_for(name: str, role: str) -> str:
    defs = GUEST_TOOLS_DEFINITIONS if role == "guest" else tools_for_role(role)
    for t in defs:
        if t["function"]["name"] == name:
            return t["function"]["description"]
    return name


if __name__ == "__main__":
    build_server().run()   # stdio transport mặc định
```

> Lưu ý khi implement: kiểm tra API `add_tool`/signature của phiên bản `mcp` đã cài (`.venv/bin/python -c "import mcp.server.fastmcp as f; help(f.FastMCP.add_tool)"`). Nếu API khác, điều chỉnh cách đăng ký nhưng GIỮ nguyên: handler chỉ nhận args của tool, `role`/`scope_team` đóng kín từ env.

**Step 2: Test build_server không nổ với các role**

Thêm vào `tests/test_mcp_server.py`:
```python
def test_build_server_ops_requires_scope(monkeypatch):
    monkeypatch.setenv("MCP_ROLE", "staff")
    monkeypatch.delenv("MCP_SCOPE_TEAM", raising=False)
    import importlib, mcp_server
    importlib.reload(mcp_server)
    import pytest
    with pytest.raises(SystemExit):
        mcp_server.build_server()

def test_build_server_admin_ok(monkeypatch):
    monkeypatch.setenv("MCP_ROLE", "admin")
    monkeypatch.setenv("MCP_SCOPE_TEAM", "")
    import importlib, mcp_server
    importlib.reload(mcp_server)
    srv = mcp_server.build_server()
    assert srv is not None
```

**Step 3: Chạy test**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_mcp_server.py -q`
Expected: PASS.

**Step 4: Smoke — server khởi động stdio không crash**

Run: `cd pipeline && MCP_ROLE=admin timeout 3 .venv/bin/python mcp_server.py < /dev/null; echo "exit=$?"`
Expected: chạy rồi timeout (exit 124) — nghĩa là vào vòng stdio ổn, không traceback import.

**Step 5: Commit**

```bash
git add pipeline/mcp_server.py pipeline/tests/test_mcp_server.py
git commit -m "feat(mcp): FastMCP wiring + entrypoint stdio, đăng ký tool theo role"
```

---

## Task 6: Tài liệu kết nối + cập nhật docs

**Files:**
- Create: `docs/project/mcp-server.md`
- Modify: `README.md` (thêm 1 dòng mục Tính năng/Vận hành trỏ tới doc)
- Modify: `docs/project/architecture.md` (1 đoạn ngắn: MCP server là adapter trên chat_tools)

**Step 1: Viết `docs/project/mcp-server.md`**

Nội dung: cách chạy (`MCP_ROLE=... MCP_SCOPE_TEAM=... python pipeline/mcp_server.py`), bảng tool theo role, mẫu config Claude Desktop (`claude_desktop_config.json` trỏ command + env), và ghi rõ ranh giới bảo mật (scope_team từ env, không từ client).

**Step 2: Kết nối thử bằng một MCP client thật**

Dùng MCP inspector hoặc Claude Desktop, cấu hình command trỏ `.venv/bin/python mcp_server.py` với `MCP_ROLE=admin`. Xác nhận list được tool và gọi `get_hot_areas` trả kết quả. Ghi kết quả vào WORKLOG.

**Step 3: Commit**

```bash
git add docs/project/mcp-server.md README.md docs/project/architecture.md
git commit -m "docs(mcp): hướng dẫn kết nối MCP server + cập nhật architecture/README"
```

---

## Task 7: Cập nhật harness story + WORKLOG

**Files:**
- Create: `docs/harness/stories/.../US-XXX-mcp-server.md` (high-risk story folder từ template)
- Modify: `WORKLOG.md`

**Step 1:** Tạo high-risk story từ `docs/harness/templates/high-risk-story/`, điền `overview/design/validation/execplan`. Ghi proof status qua `./scripts/bin/harness-cli story add` + `story update`.

**Step 2:** Thêm mục WORKLOG ngày 2026-07-02 tóm tắt: MCP server hướng A, dev-env fix, KB 6 phòng ban; kèm kết quả verify (pytest suite, test escalation guard, kết nối MCP client).

**Step 3: Commit**

```bash
git add docs/harness/stories WORKLOG.md
git commit -m "docs(harness): story + WORKLOG cho MCP server và cải thiện kèm theo"
```

---

## Thứ tự & phụ thuộc

1. **Task 0** trước tiên (mở khóa pytest).
2. **Task 1** (KB) độc lập, có thể làm song song với Task 2–5.
3. **Task 2 → 3 → 4 → 5 → 6 → 7** tuần tự (MCP).

## Verify tổng (trước khi kết thúc)

- `cd pipeline && .venv/bin/python -m pytest -q` → suite xanh, gồm `test_mcp_server.py` và `test_kb_six_departments.py`.
- Escalation guard test pass (client không đổi được scope_team).
- Kết nối MCP client thật gọi được ≥1 tool.
- `search_knowledge_base(query, scope_team="Tài chính & Thanh toán")` ra kết quả.
