-- MCP bearer tokens: map token → (role, scope_team) cho HTTP MCP server.
-- Chỉ service role (backend/MCP server) đọc bảng này; RLS bật, không policy → khóa hẳn.

create table if not exists public.mcp_tokens (
    id           uuid primary key default gen_random_uuid(),
    token_hash   text unique not null,               -- SHA-256 hex của token thô (không lưu token thô)
    label        text,                                -- ghi chú: ai/để làm gì
    role         text not null check (role in ('admin', 'manager', 'staff', 'guest')),
    scope_team   text,                                -- phòng ban; null = toàn hệ thống (admin/guest)
    active        boolean not null default true,
    created_at   timestamptz not null default now(),
    last_used_at timestamptz,

    -- ops (staff/manager) BẮT BUỘC có scope_team; admin/guest thì không.
    constraint mcp_tokens_scope_for_ops check (
        (role in ('staff', 'manager') and scope_team is not null)
        or (role in ('admin', 'guest'))
    )
);

create index if not exists idx_mcp_tokens_hash_active
    on public.mcp_tokens (token_hash) where active;

alter table public.mcp_tokens enable row level security;
-- Cố ý KHÔNG tạo policy: mọi truy cập đi qua service role (bypass RLS).
-- Client thường (anon/authenticated) không đọc/ghi được token.

comment on table public.mcp_tokens is
    'Bearer token cho HTTP MCP server; token_hash = sha256(token thô). Chỉ service role truy cập.';
