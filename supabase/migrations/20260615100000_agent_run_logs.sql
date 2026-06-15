-- Create agent_run_logs table to track LLM usage and agent execution
CREATE TABLE IF NOT EXISTS public.agent_run_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    run_id text NOT NULL,
    agent_name text NOT NULL,
    input_hash text,
    output_summary text,
    status text NOT NULL CHECK (status IN ('success', 'failed', 'fallback')),
    latency_ms integer,
    error_message text,
    
    -- LLM specific tracking
    provider text,
    model text,
    token_usage jsonb DEFAULT '{}'::jsonb,
    cost_estimate numeric(10, 6) DEFAULT 0,
    
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Index for querying recent logs
CREATE INDEX IF NOT EXISTS agent_run_logs_created_at_idx ON public.agent_run_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS agent_run_logs_run_id_idx ON public.agent_run_logs(run_id);
CREATE INDEX IF NOT EXISTS agent_run_logs_agent_name_idx ON public.agent_run_logs(agent_name);

-- RLS: Only service role can insert, admins can read
ALTER TABLE public.agent_run_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can insert agent logs"
    ON public.agent_run_logs
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Admins/Managers can view logs (requires checking profiles.role, assuming it exists)
-- Using a simpler policy for now, assuming only staff/admins will access this via an admin dashboard
CREATE POLICY "Authenticated users can view agent logs"
    ON public.agent_run_logs
    FOR SELECT
    TO authenticated
    USING (true);
