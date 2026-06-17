import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  Activity,
  Database,
  Cpu,
  Server,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Clock,
} from "lucide-react";

export const Route = createFileRoute("/_authenticated/system-health")({
  component: SystemHealthPage,
});

type HealthData = {
  checked_at: string;
  api_gateway?: { status: string; latency_ms: number; error_rate: number };
  database: { status: string; error: string | null; latency_ms?: number | null; error_rate?: number };
  llm: {
    active_provider: string;
    active_model: string;
    configured_providers: Record<string, boolean>;
    has_key?: boolean;
    latency_ms?: number | null;
  };
  ticket_workflow: {
    enabled: boolean;
    last_run_at: string | null;
    moved_to_in_progress: number;
    moved_to_resolved: number;
    last_error: string | null;
  };
  live_stream: {
    running?: boolean;
    batches_ingested?: number;
    interval_seconds?: number;
    auto_ticket?: boolean;
    [k: string]: unknown;
  };
  rate_limits: {
    chat_guest_per_hour: number;
    chat_staff_per_hour: number;
    feedback_guest_per_hour: number;
  };
};

/** Card lớn cho service chính: tên + icon + tick trạng thái + latency/error rate */
function ServiceCard({
  title,
  icon: Icon,
  ok,
  latencyMs,
  errorRate,
  footer,
}: {
  title: string;
  icon: React.ElementType;
  ok: boolean;
  latencyMs?: number | null;
  errorRate?: number | null;
  footer?: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-2xl border bg-white/70 backdrop-blur-sm p-5 shadow-[var(--shadow-card)] transition-all ${
        ok ? "border-emerald-200/70" : "border-red-200/70"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`h-10 w-10 rounded-xl grid place-items-center ${
              ok ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"
            }`}
          >
            <Icon className="h-5 w-5" />
          </div>
          <h3 className="font-display font-semibold text-gray-800 leading-tight">{title}</h3>
        </div>
        {ok ? (
          <CheckCircle2 className="h-5 w-5 text-emerald-500" />
        ) : (
          <XCircle className="h-5 w-5 text-red-500" />
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mt-5">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Latency</div>
          <div className="font-display text-2xl font-bold text-gray-800 mt-0.5">
            {latencyMs != null ? `${latencyMs}ms` : "—"}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Error Rate</div>
          <div className="font-display text-2xl font-bold text-gray-800 mt-0.5">
            {errorRate != null ? `${errorRate}%` : "—"}
          </div>
        </div>
      </div>

      {footer && <div className="mt-4">{footer}</div>}
    </div>
  );
}

/** Hàng key-value cho khối Background Jobs */
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm font-mono text-gray-500">{label}</span>
      <span className="text-sm font-mono font-medium text-gray-800">{children}</span>
    </div>
  );
}

function SystemHealthPage() {
  const { data, isLoading, isError, error, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ["system-health"],
    queryFn: async () => {
      const json = await apiFetch<{ data: HealthData }>("/api/health/services");
      return json.data;
    },
    refetchInterval: 30_000,
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <div className="rounded-xl bg-red-50 border border-red-200 p-4 text-red-700 text-sm">
          Không thể tải trạng thái hệ thống: {(error as Error)?.message ?? "Unknown error"}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const dbOk = data.database.status === "ok";
  const apiOk = (data.api_gateway?.status ?? "ok") === "ok";
  const llmOk = data.llm.has_key ?? Object.values(data.llm.configured_providers).some(Boolean);

  const stream = data.live_stream ?? {};
  const streamRunning = Boolean(stream.running);
  const updatedAt = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString("vi-VN") : "—";

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-2.5">
            <Activity className="h-8 w-8 text-xanh-deep" />
            System Health
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Giám sát độ trễ (latency), tỷ lệ lỗi và trạng thái hệ thống.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground font-mono">
            <Clock className="h-4 w-4" />
            {updatedAt}
          </span>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-3.5 py-2 text-sm font-medium text-gray-600 hover:bg-xanh-mint/20 hover:border-xanh-green/40 disabled:opacity-50 transition-colors shadow-sm"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Service cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <ServiceCard
          title="API Gateway"
          icon={Server}
          ok={apiOk}
          latencyMs={data.api_gateway?.latency_ms}
          errorRate={data.api_gateway?.error_rate ?? 0}
        />
        <ServiceCard
          title="PostgreSQL (Supabase)"
          icon={Database}
          ok={dbOk}
          latencyMs={data.database.latency_ms}
          errorRate={data.database.error_rate ?? (dbOk ? 0 : 100)}
          footer={
            data.database.error ? (
              <div className="p-2 rounded-lg bg-red-50 text-red-600 text-xs font-mono break-all">
                {data.database.error}
              </div>
            ) : undefined
          }
        />
        <ServiceCard
          title={`LLM Provider (${data.llm.active_provider})`}
          icon={Cpu}
          ok={llmOk}
          latencyMs={data.llm.latency_ms}
          errorRate={llmOk ? 0 : 100}
          footer={
            <div className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2 text-xs font-mono text-gray-600 truncate">
              Model: {data.llm.active_model}
            </div>
          }
        />
      </div>

      {/* Background Jobs */}
      <div>
        <h2 className="font-display text-xl font-bold text-xanh-deep mb-4">Background Jobs</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Live Stream */}
          <div className="rounded-2xl border border-border bg-white p-6 shadow-[var(--shadow-card)]">
            <h3 className="font-display font-semibold text-gray-800 pb-3 mb-2 border-b border-gray-100">
              Live Stream (Ingestion)
            </h3>
            <Row label="Status:">
              <span className={streamRunning ? "text-emerald-600 font-bold" : "text-amber-600 font-bold"}>
                {streamRunning ? "RUNNING" : "STOPPED"}
              </span>
            </Row>
            <Row label="Batches Ingested:">{stream.batches_ingested ?? 0}</Row>
            <Row label="Interval:">{stream.interval_seconds != null ? `${stream.interval_seconds}s` : "—"}</Row>
            <Row label="Auto Ticket:">
              <span className={stream.auto_ticket ? "text-gray-800" : "text-gray-400"}>
                {stream.auto_ticket ? "ENABLED" : "DISABLED"}
              </span>
            </Row>
          </div>

          {/* Agent Config */}
          <div className="rounded-2xl border border-border bg-white p-6 shadow-[var(--shadow-card)]">
            <h3 className="font-display font-semibold text-gray-800 pb-3 mb-2 border-b border-gray-100">
              Agent Config
            </h3>
            <Row label="Provider:">{data.llm.active_provider}</Row>
            <Row label="Model:">
              <span className="truncate max-w-[200px] inline-block align-bottom">{data.llm.active_model}</span>
            </Row>
            <Row label="Agent Available:">
              <span className={llmOk ? "text-emerald-600 font-bold" : "text-red-600 font-bold"}>
                {llmOk ? "AVAILABLE" : "UNAVAILABLE"}
              </span>
            </Row>
          </div>
        </div>
      </div>

      {/* Ticket Workflow + Rate Limits */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="rounded-2xl border border-border bg-white p-6 shadow-[var(--shadow-card)]">
          <h3 className="font-display font-semibold text-gray-800 pb-3 mb-2 border-b border-gray-100">
            Ticket Workflow (backend-worker)
          </h3>
          <Row label="Enabled:">
            <span className={data.ticket_workflow.enabled ? "text-emerald-600 font-bold" : "text-gray-400"}>
              {data.ticket_workflow.enabled ? "YES" : "NO"}
            </span>
          </Row>
          <Row label="Last run:">
            {data.ticket_workflow.last_run_at
              ? new Date(data.ticket_workflow.last_run_at).toLocaleTimeString("vi-VN")
              : "—"}
          </Row>
          <Row label="→ in_progress:">{data.ticket_workflow.moved_to_in_progress}</Row>
          <Row label="→ resolved:">{data.ticket_workflow.moved_to_resolved}</Row>
          {data.ticket_workflow.last_error && (
            <div className="mt-3 p-2 rounded-lg bg-red-50 text-red-600 text-xs font-mono break-all">
              {data.ticket_workflow.last_error}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-border bg-white p-6 shadow-[var(--shadow-card)]">
          <h3 className="font-display font-semibold text-gray-800 pb-3 mb-2 border-b border-gray-100">
            Rate Limiting
          </h3>
          <Row label="Chat (Guest):">{data.rate_limits.chat_guest_per_hour} req/hr</Row>
          <Row label="Chat (Staff):">{data.rate_limits.chat_staff_per_hour} req/hr</Row>
          <Row label="Feedback (Guest):">{data.rate_limits.feedback_guest_per_hour} req/hr</Row>
        </div>
      </div>
    </div>
  );
}
