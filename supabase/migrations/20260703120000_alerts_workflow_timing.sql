-- Timing cho workflow ticket thật + báo cáo SLA sâu (MTTA/MTTR, đúng hạn/trễ).
alter table public.alerts
    add column if not exists in_progress_at timestamptz,
    add column if not exists resolved_at    timestamptz,
    add column if not exists resolved_by     uuid references auth.users(id) on delete set null,
    add column if not exists updated_at      timestamptz;

comment on column public.alerts.resolved_at is
    'Thời điểm ticket được người thật đóng (dùng so với sla_due_at để tính đúng hạn/trễ).';
