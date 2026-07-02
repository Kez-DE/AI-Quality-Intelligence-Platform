# Spec: MCP tự động theo tài khoản — OAuth Supabase, bỏ luồng token thủ công

**Date:** 2026-07-02
**Lane:** High-risk (hard gate Auth + Public contract + External systems)
**Nhánh:** làm tiếp trên `feat/mcp-server-and-improvements` (PR #18 chưa merge — production chưa từng thấy trang token, không ship rồi gỡ)

## Bối cảnh

Luồng hiện tại (PR #18): user vào trang `/mcp-connect` bấm tạo bearer token → copy câu lệnh có token → dán vào Claude. Người dùng muốn bỏ hẳn bước này: admin nâng quyền/gán phòng cho tài khoản là MCP tự theo, nhân viên không phải tạo/copy token nào.

Khảo sát (2026-07-02) xác nhận khả thi ở cả 3 phía:

- **Supabase OAuth 2.1 Server** ([docs](https://supabase.com/docs/guides/auth/oauth-server), [trang MCP riêng](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication)): biến project thành OAuth provider cho chính user Supabase hiện có; discovery tại `https://fkopgtacyuejfzzfgtau.supabase.co/.well-known/oauth-authorization-server/auth/v1`; hỗ trợ dynamic client registration; access token là **JWT Supabase chuẩn** (`sub` = user id).
- **MCP SDK 1.28.1** (đã cài): mô hình Resource Server — `FastMCP(token_verifier=..., auth=AuthSettings(issuer_url, resource_server_url, required_scopes))`; SDK tự trả 401 + `WWW-Authenticate` + expose protected-resource metadata cho client tự discovery.
- **Claude Code/Desktop**: hỗ trợ OAuth cho remote HTTP MCP server — client tự mở browser đăng nhập, tự refresh token.

## Luồng người dùng sau khi xong

1. Một lệnh **giống hệt nhau cho mọi người**, không chứa bí mật:
   `claude mcp add --transport http xanhsm https://mcp-http-production-ffd0.up.railway.app/mcp`
2. Lần dùng đầu: browser tự mở → đăng nhập tài khoản xanhSM (email/password hoặc Google) → consent → xong.
3. Quyền resolve LIVE từ `profiles` mỗi request (cơ chế sẵn có, không đổi): admin nâng khách→nhân viên/gán phòng → cùng kết nối đó lập tức có quyền phòng ban. Token tự refresh.

Giới hạn vật lý ghi rõ: bước "add server + đăng nhập browser một lần" không thể bỏ (server không với tới máy nhân viên); cái bị bỏ là mọi thao tác token.

## Thay đổi

### 1. Supabase project

- Bật **OAuth 2.1 Server** + **dynamic client registration** (Authentication → OAuth Server). Ưu tiên tự động qua Management API/CLI; nếu bắt buộc dashboard thủ công → dừng, chỉ rõ nút cho người vận hành.

### 2. `pipeline/mcp_http.py` — chuyển sang SDK auth

- **`SupabaseTokenVerifier(TokenVerifier)`** (đặt trong `mcp_auth.py`):
  1. Thử `get_supabase().auth.get_user(token)` — hợp lệ với mọi JWT Supabase, gồm token OAuth phát → `user.id` → `_identity_from_profile(profiles...)` (tái dùng nguyên hàm hiện có).
  2. Thất bại → fallback `verify_token` bảng `mcp_tokens` (bearer máy-tới-máy cho script/CI/admin, cấp qua CLI `mcp_auth.py`).
  3. Cả hai fail → None → SDK trả 401.
  - Trả `AccessToken(token=..., client_id=..., scopes=[], claims={"role": ..., "scope_team": ...})`.
- `FastMCP(..., token_verifier=verifier, auth=AuthSettings(issuer_url="https://fkopgtacyuejfzzfgtau.supabase.co/auth/v1", resource_server_url="<railway>/mcp"))`. Bỏ `AuthMiddleware` tự chế (giữ `/health` — route riêng ngoài app MCP hoặc mount).
- Tool handler đọc identity từ auth context của SDK (`get_access_token().claims`) thay cho ContextVar tự quản.

### 3. Xóa luồng token self-service

- Xóa `app/src/routes/_authenticated/mcp-connect.tsx` + nav item "Kết nối MCP" trong `AppShell.tsx`.
- Xóa `POST /api/mcp/token` trong `pipeline/main.py`.
- GIỮ: `mcp_auth.py` (CLI cấp token máy + verify fallback), bảng `mcp_tokens`, stdio server local, role gate `call_tool`, scope phòng ban.

### 4. Docs

- `docs/project/mcp-server.md`: viết lại mục kết nối — luồng OAuth một lệnh; bearer chỉ còn là đường máy-tới-máy do admin cấp.
- Decision `docs/harness/decisions/0011-mcp-oauth-supabase.md` + đăng ký harness CLI.
- WORKLOG.

## Validation

- Unit: verifier — JWT hợp lệ→identity đúng theo profile; JWT rác→fallback bearer; cả hai fail→None; ops chưa gán phòng→guest.
- E2E server-side thật (không cần browser): password-grant JWT của tài khoản demo (admin + staff có phòng) → gọi `/mcp` trên local rồi trên Railway → list tools + call tool đúng scope; staff bị chặn tool cấp điều hành.
- Discovery: `GET /.well-known/oauth-protected-resource` (server mình) trỏ đúng issuer Supabase; `GET .well-known/oauth-authorization-server/auth/v1` (Supabase) trả metadata.
- 401 khi không token, `WWW-Authenticate` có resource metadata.
- Client thật: `claude mcp add` không header → xác nhận client nhận diện OAuth (bước đăng nhập browser cuối do người dùng làm — cung cấp lệnh sẵn).
- Full pytest + tsc.

## Quyết định kèm theo (chốt trong phiên brainstorm)

- Giữ bearer fallback (không xóa sạch): đường máy-tới-máy cho script/CI, chi phí ~0 vì code đã test sẵn.
- Làm trên nhánh PR #18, không merge trước rồi gỡ.
