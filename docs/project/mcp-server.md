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

## Xác thực

Mỗi request mang `Authorization: Bearer <token>`. Middleware tra bảng `mcp_tokens` →
`(role, scope_team)`. Thiếu/sai token → 401. `scope_team` lấy từ token, không từ args →
không leo quyền; role kiểm ở `call_tool` (tool ngoài quyền trả thông báo chặn).

## Cấp phát / thu hồi token

```bash
# cấp token (in ra token thô một lần — lưu lại ngay)
cd pipeline
.venv/bin/python mcp_auth.py admin                     # admin, toàn hệ thống
.venv/bin/python mcp_auth.py manager "CSKH"            # manager phòng CSKH
.venv/bin/python mcp_auth.py staff "Tài chính & Thanh toán"

# thu hồi: set active=false trong bảng mcp_tokens (theo label hoặc id)
```

Bảng `mcp_tokens` (migration `20260702000000_mcp_tokens.sql`): chỉ lưu SHA-256 của token,
RLS khóa service-role. staff/manager bắt buộc có `scope_team`; admin/guest thì null.

## Cấu hình client (Claude Desktop / Claude Code)

```bash
claude mcp add --transport http xanhsm-quality-remote \
  https://mcp-http-production-ffd0.up.railway.app/mcp \
  --header "Authorization: Bearer <TOKEN_CỦA_BẠN>"
```

Mỗi người dùng token riêng → thấy đúng quyền phòng ban của mình. Không cần clone repo hay
chạy gì ở máy.

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
