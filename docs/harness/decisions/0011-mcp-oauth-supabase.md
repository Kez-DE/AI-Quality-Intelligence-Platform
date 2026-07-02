# 0011 MCP OAuth qua Supabase OAuth 2.1 Server

Date: 2026-07-02

## Status

Accepted (thay phần "cấp phát token thủ công" của [0010](0010-mcp-http-token-auth-railway.md))

## Context

Bản 0010 cho nhiều người dùng nhưng mỗi người vẫn phải tự tạo bearer token + dán câu lệnh
vào Claude. Yêu cầu: bỏ hẳn thao tác token — admin nâng quyền/gán phòng cho tài khoản là
MCP tự dùng được, nhân viên chỉ đăng nhập. Chạm hard gate: Auth + Public contract +
External systems.

## Decision

`mcp_http.py` chuyển sang **OAuth 2.1 Resource Server** của MCP SDK
(`FastMCP(token_verifier=SupabaseTokenVerifier, auth=AuthSettings(issuer=Supabase, resource=Railway))`),
với **Supabase OAuth 2.1 Server làm Authorization Server** (bật qua Management API:
`oauth_server_enabled` + `oauth_server_allow_dynamic_registration`,
`authorization_path=/oauth/authorize`).

Client kết nối bằng một lệnh không chứa bí mật; SDK trả 401 + `WWW-Authenticate` →
client tự discovery (`/.well-known/oauth-protected-resource`) → dynamic client registration
→ browser login Supabase → JWT. `SupabaseTokenVerifier` verify JWT (`auth.get_user`) rồi
resolve role/phòng LIVE từ `profiles`. Bearer bảng `mcp_tokens` giữ làm fallback máy-tới-máy.

Bỏ luồng self-service: xóa trang `/mcp-connect` + `POST /api/mcp/token`.

## Alternatives Considered

1. **Giữ token thủ công (0010)**: loại — không đạt yêu cầu "auto, không token".
2. **Tự viết OAuth Authorization Server**: loại — Supabase đã là AS chuẩn cho chính user
   của mình, dựng AS riêng là thừa và rủi ro bảo mật.
3. **Xóa sạch bearer**: loại — mất đường máy-tới-máy (script/CI không có browser). Giữ
   bearer làm fallback, chi phí ~0.

## Consequences

Positive:

- Nhân viên: một lệnh + đăng nhập một lần, không token. Admin đổi quyền → tự áp dụng.
- Quyền vẫn resolve live từ `profiles`; JWT tự refresh; token không lộ được vì không có
  bước copy token.

Tradeoffs:

- Phụ thuộc feature OAuth 2.1 Server của Supabase (đã bật trên project ref
  `fkopgtacyuejfzzfgtau`).
- Bước "add server + login browser" một lần không bỏ được (giới hạn vật lý).

## Giới hạn đã biết (review cuối 2026-07-02)

- **Chưa bind audience (RFC 8707):** `auth.get_user()` chỉ xác nhận JWT hợp lệ cho project,
  KHÔNG kiểm token có đúng audience/resource là MCP server này. Hệ quả: một JWT session của
  web-app cùng project cũng vào được `/mcp`. KHÔNG phải leo quyền (quyền vẫn resolve từ
  `profiles` của chính user đó), rủi ro confused-deputy thấp vì Supabase là AS duy nhất, một
  resource. Cần siết nếu mở cho client bên thứ ba.
- **Tài khoản mới (signup) = `guest`** (migration `20260616000000`): qua MCP chỉ
  `submit_feedback` — đúng bằng quyền guest sẵn có ở chat khách, không mở rộng phơi nhiễm.

## Follow-Up

- Cân nhắc consent screen / giới hạn scope OIDC + bind audience nếu mở cho client bên thứ ba.
- Nếu Supabase đổi endpoint OAuth → cập nhật `issuer_url`.
