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

## Kiểm thử

- `pipeline/tests/test_mcp_server.py`: phân quyền theo role + guard chống leo scope_team.
- Smoke: `MCP_ROLE=admin .venv/bin/python mcp_server.py < /dev/null` khởi động và tắt sạch,
  không traceback.
