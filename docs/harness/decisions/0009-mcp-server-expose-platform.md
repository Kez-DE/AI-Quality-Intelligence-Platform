# 0009 Expose platform qua MCP server (identity server-side)

Date: 2026-07-02

## Status

Accepted

## Context

Cần cho agent ngoài (Claude Desktop, MCP client khác) truy vấn được platform. Chat
agent đã có sẵn lớp tool đúng hình dạng MCP: `pipeline/agent/chat_tools.py` với 6 hàm
thuần, map phân quyền theo role (`tools_for_role`), và scope theo phòng ban ép ở
`execute_tool`. Việc mở một bề mặt truy cập mới chạm hard gate: Authorization, Public
contract, External systems.

## Decision

Dựng một MCP server stdio (`pipeline/mcp_server.py`) làm **adapter mỏng** bọc quanh
`chat_tools.py` — không sửa file đó. Danh tính (role + phòng ban) **cố định phía server**
qua env `MCP_ROLE` / `MCP_SCOPE_TEAM`, không lấy từ caller. Mọi tool call đi qua
`execute_tool(..., scope_team=<env>)`; `scope_team` không bao giờ đọc từ tham số tool.

## Alternatives Considered

1. **Pipeline đi consume MCP server ngoài** (vd Supabase MCP) thay lớp tool nội bộ:
   loại — rewrite code đang chạy tốt, và server generic bỏ qua department scoping =
   regression bảo mật.
2. **HTTP/SSE server đa tenant** map token → (role, team): hoãn — demo cohort chỉ cần
   một identity mỗi cấu hình; thêm phức tạp không cần thiết lúc này.

## Consequences

Positive:

- Tái dùng toàn bộ logic + RBAC sẵn có; thêm khả năng mới không đụng agent nội bộ.
- Ranh giới bảo mật rõ: client không leo được ra khỏi phòng ban (test escalation guard).

Tradeoffs:

- Một identity cho mỗi tiến trình server (đổi role/phòng = đổi env + chạy lại).
- Thêm một dependency `mcp` (FastMCP).

## Follow-Up

- Nếu cần nhiều người dùng đồng thời với role/phòng khác nhau → làm HTTP server map
  token → identity (đã ghi là out-of-scope hiện tại).
