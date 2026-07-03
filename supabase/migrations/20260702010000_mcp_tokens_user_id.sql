-- MCP token gắn với user_id thay vì lưu role/phòng tĩnh.
-- Lý do: quyền phải theo profile HIỆN TẠI — admin nâng khách→nhân viên/gán phòng thì
-- token cũ tự phản ánh, không phải cấp lại. role/scope_team giờ resolve live từ profiles.

alter table public.mcp_tokens
    add column if not exists user_id uuid references auth.users(id) on delete cascade;

-- role/scope_team không còn là nguồn sự thật → gỡ ràng buộc cứng.
alter table public.mcp_tokens drop constraint if exists mcp_tokens_scope_for_ops;
alter table public.mcp_tokens alter column role drop not null;

create index if not exists idx_mcp_tokens_user on public.mcp_tokens (user_id);

comment on column public.mcp_tokens.user_id is
    'Chủ token. Quyền (role, phòng) resolve LIVE từ profiles mỗi request, không lưu tĩnh.';
