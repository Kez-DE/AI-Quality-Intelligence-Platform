# 0010 HTTP MCP server + auth token→role/phòng (deploy Railway)

Date: 2026-07-02

## Status

Accepted

## Context

Bản stdio (decision 0009) chỉ chạy local, một identity mỗi tiến trình. Để nhiều người
dùng qua mạng mà không cần cài local, cần transport HTTP + xác thực per-request. Chạm hard
gate: Authorization, Public contract, External systems, Cross-platform (deploy).

## Decision

Thêm `pipeline/mcp_http.py`: FastMCP `streamable-http` (stateless) sau một ASGI middleware
xác thực. Mỗi request mang `Authorization: Bearer <token>`; middleware tra bảng
`mcp_tokens` → identity `(role, scope_team)`, set vào ContextVar cho request đó. Tool
handler đọc identity này; `scope_team` từ token, KHÔNG từ args. Role kiểm ở `call_tool`
(đăng ký sẵn mọi tool, chặn theo role mỗi request).

Auth model = **bảng token** (`token→role/phòng`), KHÔNG dùng Supabase JWT passthrough: MCP
client (Claude Desktop) không refresh được JWT hết hạn mỗi giờ; token bảng thì revoke được,
đa người dùng, admin cấp phát.

Deploy Railway: service `mcp-http` thứ 7, dùng `pipeline/Dockerfile.mcp`, chọn qua biến
`RAILWAY_DOCKERFILE_PATH`. Tắt DNS-rebinding protection của MCP (chỉ cho localhost →
Railway host bị 421); an toàn vì bearer token là cổng gác.

## Alternatives Considered

1. **Supabase JWT passthrough**: loại — JWT hết hạn 1h, Claude Desktop không refresh được.
2. **Static token map trong env**: loại — không revoke/không quản đa người dùng được.
3. **Giữ nguyên stdio**: không đạt yêu cầu "nhiều người, không cần local".

## Consequences

Positive:

- Nhiều người dùng qua URL, mỗi người một token → role/phòng riêng, không cần cài local.
- Token revoke được (set `active=false`); `scope_team` ép server-side (test escalation qua
  mạng: hỏi Safety vẫn ra CSKH).

Tradeoffs:

- Token là bearer tĩnh: lộ token = lộ quyền của token đó → phải bảo mật + xoay khi cần.
- Tool list hiện đủ 6 cho mọi role (chặn ở tầng thực thi, không ẩn khỏi list) do stateless
  HTTP một tập tool chung.

## Follow-Up

- API/endpoint cho admin cấp phát + revoke token (hiện dùng `python mcp_auth.py <role> [team]`).
- Cân nhắc rate-limit và log truy cập token.
