-- Structured ticket routing metadata. Legacy Markdown fields remain readable
-- during the transition but are no longer the source of truth.
ALTER TABLE public.alerts
  ADD COLUMN IF NOT EXISTS assigned_team TEXT,
  ADD COLUMN IF NOT EXISTS topic TEXT,
  ADD COLUMN IF NOT EXISTS priority TEXT,
  ADD COLUMN IF NOT EXISTS ticket_type TEXT NOT NULL DEFAULT 'incident',
  ADD COLUMN IF NOT EXISTS routing_source TEXT,
  ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMPTZ;

UPDATE public.alerts
SET assigned_team = CASE
  WHEN lower(substring(description FROM '\*\*Assigned Team:\*\*\s*([^\n\r]+)')) LIKE '%safety%' THEN 'Safety'
  WHEN lower(substring(description FROM '\*\*Assigned Team:\*\*\s*([^\n\r]+)')) LIKE '%cskh%' THEN 'CSKH'
  WHEN lower(substring(description FROM '\*\*Assigned Team:\*\*\s*([^\n\r]+)')) LIKE '%it%' THEN 'IT'
  WHEN lower(substring(description FROM '\*\*Assigned Team:\*\*\s*([^\n\r]+)')) LIKE '%pricing%' THEN 'Pricing'
  WHEN lower(substring(description FROM '\*\*Assigned Team:\*\*\s*([^\n\r]+)')) LIKE '%marketing%' THEN 'Marketing'
  WHEN substring(description FROM '\*\*Assigned Team:\*\*\s*([^\n\r]+)') IS NOT NULL THEN 'Vận hành'
  ELSE assigned_team
END
WHERE assigned_team IS NULL;

UPDATE public.alerts
SET priority = substring(description FROM '\*\*Priority:\*\*\s*([^\n\r]+)')
WHERE priority IS NULL AND description LIKE '%**Priority:**%';

CREATE INDEX IF NOT EXISTS idx_alerts_assigned_team_created
  ON public.alerts(assigned_team, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_routing_group
  ON public.alerts(assigned_team, area, topic, created_at DESC);

COMMENT ON COLUMN public.alerts.assigned_team IS
  'Canonical RBAC department: IT, Safety, CSKH, Vận hành, Pricing, Marketing';
COMMENT ON COLUMN public.alerts.ticket_type IS
  'incident for operational risk, opportunity for positive Marketing spikes';
