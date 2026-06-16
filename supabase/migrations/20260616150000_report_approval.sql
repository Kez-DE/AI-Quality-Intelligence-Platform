-- Add approval fields to department_reports
ALTER TABLE public.department_reports ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT false;
ALTER TABLE public.department_reports ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;
ALTER TABLE public.department_reports ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
