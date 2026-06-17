import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  Activity,
  Database,
  Bot,
  Radio,
  Shield,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
} from "lucide-react";

export const Route = createFileRoute("/_authenticated/system-health")({
  component: SystemHealthPage,
});

type HealthData = {
  checked_at: string;
  database: { status: string; error: string | null };
  llm: {
    active_provider: string;
    active_model: string;
    configured_providers: Record<string, boolean>;
  };
  ticket_workflow: {
    enabled: boolean;
    last_run_at: string | null;
    moved_to_in_progress: number;
    moved_to_resolved: number;
    last_error: string | null;
  };
  live_stream: Record<string, unknown>;
  rate_limits: {
    chat_guest_per_hour: number;
    chat_staff_per_hour: number;
    feedback_guest_per_hour: number;
  };
};

function StatusBadge({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
        ok
          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
          : "bg-red-50 text-red-700 border border-red-200"
      }`}
    >
      {ok ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {label ?? (ok ? "Online" : "Error")}
    </span>
  );
}

function Card({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="h-5 w-5 text-gray-500" />
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function SystemHealthPage() {
  const { data, isLoading, isError, error, refetch, dataUpdatedAt } = useQuery({
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
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 text-sm">
          Không thể tải trạng thái hệ thống: {(error as Error)?.message ?? "Unknown error"}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const dbOk = data.database.status === "ok";
  const llmOk = Object.values(data.llm.configured_providers).some(Boolean);
  const workflowOk = data.ticket_workflow.enabled && !data.ticket_workflow.last_error;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Activity className="h-6 w-6 text-blue-600" />
            System Health
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Cập nhật lần cuối: {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString("vi-VN") : "—"}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Overall Status */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className={`rounded-xl p-4 border ${dbOk ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"}`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Database</span>
            <StatusBadge ok={dbOk} />
          </div>
        </div>
        <div className={`rounded-xl p-4 border ${llmOk ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"}`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">LLM Provider</span>
            <StatusBadge ok={llmOk} label={llmOk ? data.llm.active_provider : "No key"} />
          </div>
        </div>
        <div className={`rounded-xl p-4 border ${workflowOk ? "border-emerald-200 bg-emerald-50" : "border-yellow-200 bg-yellow-50"}`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Ticket Workflow</span>
            <StatusBadge ok={workflowOk} label={workflowOk ? "Active" : data.ticket_workflow.last_error ? "Error" : "Disabled"} />
          </div>
        </div>
      </div>

      {/* Detail Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Database */}
        <Card title="Database (Supabase)" icon={Database}>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Status</span>
              <StatusBadge ok={dbOk} />
            </div>
            {data.database.error && (
              <div className="mt-2 p-2 rounded bg-red-50 text-red-600 text-xs font-mono break-all">
                {data.database.error}
              </div>
            )}
          </div>
        </Card>

        {/* LLM Providers */}
        <Card title="LLM Providers" icon={Bot}>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Active</span>
              <span className="font-medium">{data.llm.active_provider} / {data.llm.active_model}</span>
            </div>
            <div className="mt-3 space-y-1.5">
              {Object.entries(data.llm.configured_providers).map(([provider, hasKey]) => (
                <div key={provider} className="flex items-center justify-between">
                  <span className="text-gray-600 capitalize">{provider}</span>
                  <StatusBadge ok={hasKey as boolean} label={hasKey ? "Configured" : "No key"} />
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Ticket Workflow */}
        <Card title="Ticket Workflow (backend-worker)" icon={Radio}>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Enabled</span>
              <StatusBadge ok={data.ticket_workflow.enabled} label={data.ticket_workflow.enabled ? "Yes" : "No"} />
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Last run</span>
              <span className="text-gray-700">{data.ticket_workflow.last_run_at ? new Date(data.ticket_workflow.last_run_at).toLocaleTimeString("vi-VN") : "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">→ in_progress</span>
              <span className="font-medium">{data.ticket_workflow.moved_to_in_progress}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">→ resolved</span>
              <span className="font-medium">{data.ticket_workflow.moved_to_resolved}</span>
            </div>
            {data.ticket_workflow.last_error && (
              <div className="mt-2 p-2 rounded bg-red-50 text-red-600 text-xs font-mono break-all">
                {data.ticket_workflow.last_error}
              </div>
            )}
          </div>
        </Card>

        {/* Rate Limits */}
        <Card title="Rate Limiting" icon={Shield}>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Chat (Guest)</span>
              <span className="font-medium">{data.rate_limits.chat_guest_per_hour} req/hr</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Chat (Staff)</span>
              <span className="font-medium">{data.rate_limits.chat_staff_per_hour} req/hr</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Feedback (Guest)</span>
              <span className="font-medium">{data.rate_limits.feedback_guest_per_hour} req/hr</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Live Stream (raw JSON for now) */}
      {data.live_stream && Object.keys(data.live_stream).length > 0 && (
        <Card title="Live Stream Status" icon={Radio}>
          <pre className="text-xs text-gray-600 font-mono bg-gray-50 p-3 rounded-lg overflow-x-auto">
            {JSON.stringify(data.live_stream, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}
