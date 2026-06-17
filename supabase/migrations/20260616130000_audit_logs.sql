-- Audit log: ghi lại mọi thay đổi quyền/xoá user bởi admin.
CREATE TABLE public.audit_logs (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  actor_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_email TEXT,
  action TEXT NOT NULL,          -- 'role_change' | 'user_delete' | 'bulk_approve'
  target_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  target_email TEXT,
  details JSONB DEFAULT '{}',    -- e.g. {"old_role": "guest", "new_role": "staff"}
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_created_at ON public.audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_actor ON public.audit_logs(actor_id);

GRANT SELECT, INSERT ON public.audit_logs TO authenticated;
GRANT ALL ON public.audit_logs TO service_role;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Chỉ admin đọc được audit log qua Supabase client trực tiếp
CREATE POLICY "Audit logs readable by admin" ON public.audit_logs
  FOR SELECT TO authenticated
  USING (public.is_admin());

-- Insert chỉ qua service_role (backend)
CREATE POLICY "Audit logs insertable by service_role" ON public.audit_logs
  FOR INSERT TO service_role
  WITH CHECK (true);
