# MCP Server — expose platform ra ngoài

`pipeline/mcp_server.py` là một MCP server (stdio) cho agent ngoài (Claude Desktop, MCP
inspector, ...) truy vấn dữ liệu chất lượng dịch vụ. Nó là adapter mỏng bọc quanh
`pipeline/agent/chat_tools.py`, không lặp lại logic.

## Danh tính cố định phía server

Server đọc danh tính từ env lúc khởi động, client KHÔNG truyền được:

- `MCP_ROLE` — `admin` | `manager` | `staff` | `guest` (mặc định `guest`).
- `MCP_SCOPE_TEAM` — tên phòng ban (vd `Tài chính & Thanh toán`); rỗng = toàn hệ thống,
  chỉ hợp lệ khi role `admin`. Bắt buộc khi role `staff`/`manager`.

`scope_team` luôn lấy từ config server; tham số tool không bao giờ đổi được phòng ban thực
thi. Đây là ranh giới bảo mật — MCP client không leo ra khỏi phòng của mình.

## Tool theo role

| Role | Tool thấy được |
|---|---|
| guest | `submit_feedback` |
| staff | `search_knowledge_base`, `get_team_priority_tasks` |
| manager | như staff + `get_feedback_summary`, `get_hot_areas`, `get_sla_tickets` |
| admin | toàn bộ tool, scope toàn hệ thống |

## Chạy local

```bash
cd pipeline
MCP_ROLE=admin MCP_SCOPE_TEAM="" .venv/bin/python mcp_server.py
```

Cần các env Supabase/LLM như backend (đọc từ `.env`).

## Cấu hình Claude Desktop

Thêm vào `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "xanhsm-quality": {
      "command": "/đường/dẫn/pipeline/.venv/bin/python",
      "args": ["/đường/dẫn/pipeline/mcp_server.py"],
      "env": {
        "MCP_ROLE": "manager",
        "MCP_SCOPE_TEAM": "CSKH"
      }
    }
  }
}
```

Khởi động lại Claude Desktop, kiểm tra list được tool và gọi thử (vd `get_hot_areas`).

## Kiểm thử (stdio)

- `pipeline/tests/test_mcp_server.py`: phân quyền theo role + guard chống leo scope_team.
- Smoke: `MCP_ROLE=admin .venv/bin/python mcp_server.py < /dev/null` khởi động và tắt sạch,
  không traceback.

---

# Bản HTTP (multi-user, deploy Railway)

`pipeline/mcp_http.py` = FastMCP streamable-http + auth token, cho **nhiều người dùng qua
URL, không cần cài local**. Đã deploy service `mcp-http` trên Railway.

**URL production:** `https://mcp-http-production-ffd0.up.railway.app/mcp` (health: `/health`).

## Xác thực — OAuth theo TÀI KHOẢN, tự động, không token

Server là **OAuth 2.1 Resource Server**; **Supabase là Authorization Server** (đã bật OAuth
2.1 Server + dynamic client registration trên project). Không ai phải tạo/copy token.

Luồng: client (Claude) gọi `/mcp` không token → server trả **401 + `WWW-Authenticate`** kèm
`resource_metadata` → client đọc `/.well-known/oauth-protected-resource/mcp` → thấy AS là
Supabase → tự đăng ký client (DCR) + mở browser cho user đăng nhập tài khoản xanhSM →
Supabase phát **JWT** → mọi request sau gắn JWT đó (client tự refresh).

`SupabaseTokenVerifier` (trong `mcp_auth.py`) verify mỗi request: JWT Supabase →
`auth.get_user()` → `user.id` → đọc `profiles.role`+`department` **ngay lúc đó** → identity.
(Fallback: bearer bảng `mcp_tokens` cho đường máy-tới-máy — xem dưới.)

Ánh xạ profile → quyền MCP:

| Profile | Quyền MCP |
|---|---|
| role `admin` | mọi tool, toàn hệ thống |
| `manager`/`staff` + đã gán phòng | tool theo role, scoped đúng phòng đó |
| `manager`/`staff` CHƯA gán phòng | chỉ `submit_feedback` (như khách) |
| role `guest` (tài khoản mới) | chỉ `submit_feedback` |

Vì resolve LIVE, **admin nâng khách → nhân viên/quản lý và gán phòng thì kết nối cũ tự có
quyền phòng đó ngay — không cấp lại gì, không cấu hình lại Claude.** `scope_team` lấy từ
profile không từ args (không leo quyền); JWT hợp lệ nhưng user không có profile → bị từ chối
(fail-closed).

## Kết nối client (Claude Desktop / Claude Code) — một lệnh, không bí mật

```bash
claude mcp add --transport http xanhsm-quality-remote \
  https://mcp-http-production-ffd0.up.railway.app/mcp
```

Lệnh **giống nhau cho mọi người**. Lần dùng đầu Claude tự mở browser → đăng nhập tài khoản
xanhSM → xong. Không clone repo, không chạy gì ở máy, không dán token. Bước "add + đăng nhập
một lần" là giới hạn vật lý duy nhất (server không với tới máy user).

## Đường máy-tới-máy (script / CI) — bearer do admin cấp

Khi cần kết nối không-browser (script, cron, agent tự động), admin cấp bearer token theo
`user_id` — quyền vẫn theo profile của user đó, resolve live:

```bash
cd pipeline && .venv/bin/python mcp_auth.py <user_id> "nhãn ghi chú"   # in token 1 lần
# rồi: claude mcp add --transport http xanhsm ... --header "Authorization: Bearer <token>"
```

Bảng `mcp_tokens` (migration `20260702000000` + `20260702010000`): lưu SHA-256 token +
`user_id`, RLS khóa service-role. Thu hồi: `active=false` theo `label`/`id`. Xóa tài khoản
→ token tự xóa (FK cascade).

## Deploy lại

Service `mcp-http` (Railway project, env production) build từ `pipeline/Dockerfile.mcp`
(chọn qua biến `RAILWAY_DOCKERFILE_PATH=pipeline/Dockerfile.mcp`). Env cần: `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_KEY`, `COHERE_API_KEY`. Deploy: `railway up --service
mcp-http`. `$PORT` do Railway inject.

## Kiểm thử (HTTP)

- `pipeline/tests/test_mcp_auth.py`, `test_mcp_http.py`: hash/verify token, 401, ContextVar
  identity, role gate, unknown-role → không tool.
- E2E production: token manager CSKH gọi `get_feedback_summary` ra "Phòng CSKH"; hỏi task
  phòng "Safety" vẫn bị ép về CSKH (scope guard qua mạng).
