# Spec: MCP Server (expose platform) + hai cải thiện kèm theo

**Date:** 2026-07-02
**Lanes:** MCP server = **High-risk** (hard gate: Authorization + Public contract + External systems). Dev-env fix = **Tiny**. KB 6 phòng ban = **Normal**.

## Bối cảnh

Dự án chưa dùng MCP ở đâu cả. Nhưng chat agent đã có sẵn một lớp tool hình dạng đúng chuẩn MCP: `pipeline/agent/chat_tools.py` có 6 hàm thuần trả về string, một map phân quyền theo vai trò (`tools_for_role`), và scope theo phòng ban ép ở `execute_tool`. Đây là bề mặt để dựng MCP server mà không phải viết lại logic.

Phiên brainstorm chốt hướng **A — expose platform thành MCP server** (không phải cho pipeline đi gọi MCP server ngoài, vì hướng đó rewrite code đang chạy tốt và có nguy cơ bỏ qua department scoping).

Hai việc kèm theo cùng phát hiện khi chạy dự án:
- `pipeline/.venv` đang chạy Python 3.14.6 trong khi Docker/production pin 3.11-slim → chạy full `pytest` local crash ở teardown (`ValueError: I/O operation on closed file`), không lấy được kết quả suite sạch.
- KB nội bộ còn dùng nhãn legacy (Safety/CSKH/Vận hành/IT), 3 phòng chuẩn (Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận) chưa có tài liệu → `search_knowledge_base` không phủ đủ 6 phòng.

---

## 1. MCP Server — `pipeline/mcp_server.py` (High-risk)

### Nguyên tắc thiết kế
Adapter mỏng bọc quanh code sẵn có. **Không sửa** `chat_tools.py` (nó đã có `tools_for_role`, `execute_tool`, `execute_guest_tool`).

### Transport & dependency
- Dùng official `mcp` Python SDK (FastMCP), transport **stdio** → Claude Desktop và mọi MCP client kết nối được.
- Thêm một dependency: `mcp`. Không thể làm MCP mà không có thư viện MCP; tự viết protocol là lựa chọn tệ hơn.

### Danh tính cố định phía server (KHÔNG lấy từ caller)
Đọc từ env lúc khởi động:
- `MCP_ROLE` — một trong `admin` / `manager` / `staff` / `guest`.
- `MCP_SCOPE_TEAM` — tên phòng ban, rỗng = toàn hệ thống (chỉ hợp lệ khi role = admin).
- Tái dùng env Supabase/LLM mà pipeline vốn đã cần.

### Đăng ký tool
- Role `guest` → chỉ đăng ký `submit_feedback`, gọi qua `execute_guest_tool`.
- Role khác → đăng ký đúng tập `tools_for_role(MCP_ROLE)` trả về, mỗi tool là wrapper gọi `execute_tool(name, args, scope_team=<MCP_SCOPE_TEAM>)`.
- Kết quả string của tool trả về nguyên văn làm nội dung MCP tool result.

### Ranh giới bảo mật (điểm cốt lõi của spec này)
- `scope_team` lấy từ config server, **không bao giờ** đọc từ tham số tool → MCP client không thể leo ra khỏi phòng ban của mình.
- `MCP_ROLE` quyết định tool nào tồn tại; client không thấy tool ngoài quyền.
- `submit_feedback` vẫn mask PII qua `mask_pii` như hiện tại (đi qua `execute_guest_tool`).

### Ngoài phạm vi (ghi lại làm tương lai)
- HTTP/SSE server đa tenant, map token → (role, team) cho nhiều người dùng đồng thời. Demo hiện tại không cần; một identity mỗi cấu hình là đủ.

### Validation
- Test in-process: server cấu hình role `staff` **không** expose `get_feedback_summary` (chỉ `search_knowledge_base` + `get_team_priority_tasks`).
- Test escalation guard: client truyền `scope_team`/`team_name` khác trong args **không** đổi được phòng ban thực thi — vẫn ép về `MCP_SCOPE_TEAM`.
- Test guest: chỉ có `submit_feedback`, và nội dung được mask PII.
- Kết nối thử bằng một MCP client (Claude Desktop hoặc `mcp` inspector) gọi được ít nhất 1 tool.
- Ghi decision record `docs/harness/decisions/NNNN-mcp-server-expose-platform.md` (hard gate).

---

## 2. Dev-env fix: Python 3.14 → 3.11/3.12 (Tiny)

- Tạo lại `pipeline/.venv` bằng Python 3.11 hoặc 3.12 (khớp Dockerfile 3.11-slim), cài lại từ `requirements*.txt`.
- Ghi bản pin Python vào README (mục cài đặt) để lần sau không dựng nhầm.

### Validation
- `.venv/bin/python -m pytest -q` chạy trọn suite, in ra kết quả (kỳ vọng ~68 passed / 3 skipped), không crash teardown.

---

## 3. KB cho 3 phòng ban còn thiếu (Normal)

- Soạn tài liệu KB cho **Tài chính & Thanh toán**, **Sản phẩm**, **Quản lý Rủi ro & Gian lận** dưới `data/knowledge_base/`, có YAML frontmatter `department:` đúng tên phòng chuẩn.
- Chạy lại bước embed/index để `search_knowledge_base` phủ đủ 6 phòng (dùng đúng script index hiện có — xác minh script trong `pipeline/agent/rag_engine.py`/`knowledge_base.py` khi làm plan).

### Validation
- `search_knowledge_base(query, scope_team="Tài chính & Thanh toán")` trả về tài liệu mới, không rỗng.
- Không làm hỏng KB legacy đang có (query phòng cũ vẫn ra kết quả).

---

## Không thay đổi

- `chat_tools.py` — giữ nguyên, MCP server chỉ gọi vào.
- Chat agent, RAG engine, model router — không đụng.
- Schema DB, RLS — không đụng (MCP server dùng service role như backend).
