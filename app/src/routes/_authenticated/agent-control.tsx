import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch, useMe } from "@/lib/api";
import {
  Bot,
  Play,
  RefreshCw,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Zap,
  Filter,
  ScrollText,
  Activity,
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/agent-control")({
  component: AgentControlPage,
});

// ── Kiểu dữ liệu khớp /api/agent/stats ──
type AgentStat = {
  name: string;
  label: string;
  step: number;
  description: string;
  uses_llm: boolean;
  enabled: boolean;
  flag: string | null;
  runs: number;
  success: number;
  failed: number;
  fallback: number;
  error_rate: number;
  avg_latency_ms: number;
  last_run: string | null;
};

type StatsData = {
  window_hours: number;
  worker_enabled: boolean;
  interval_seconds: number;
  total_runs: number;
  db_error: string | null;
  agents: AgentStat[];
};

type AiLogEntry = {
  ts: string;
  agent: string;
  status: string;
  run_id?: string;
  latency_ms?: number;
  summary?: string;
  error?: string;
  provider?: string;
  model?: string;
};

function timeAgo(iso: string | null): string {
  if (!iso) return "chưa chạy";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Date.now() - then;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "vừa xong";
  if (m < 60) return `${m} phút trước`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} giờ trước`;
  return `${Math.floor(h / 24)} ngày trước`;
}

function statusColor(status: string): string {
  switch (status) {
    case "success":
      return "text-emerald-500";
    case "failed":
      return "text-red-500";
    case "fallback":
      return "text-amber-500";
    default:
      return "text-muted-foreground";
  }
}

/** Thẻ 1 agent trong dây chuyền. */
function AgentCard({ a }: { a: AgentStat }) {
  const healthy = a.error_rate < 0.2;
  return (
    <div className="rounded-2xl border border-border bg-card/80 backdrop-blur-sm p-5 shadow-[var(--shadow-card)] transition-all hover:shadow-[var(--shadow-green)] hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`h-10 w-10 shrink-0 rounded-xl grid place-items-center font-display font-bold ${
              a.enabled
                ? "bg-xanh-mint text-xanh-deep"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {a.step}
          </div>
          <div className="min-w-0">
            <h3 className="font-display font-semibold text-foreground leading-tight truncate">
              {a.label}
            </h3>
            <p className="text-[11px] font-mono text-muted-foreground truncate">{a.name}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          {a.enabled ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-mono font-semibold px-2 py-0.5">
              <CheckCircle2 className="h-3 w-3" /> BẬT
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted text-muted-foreground text-[10px] font-mono font-semibold px-2 py-0.5">
              <XCircle className="h-3 w-3" /> TẮT
            </span>
          )}
          {a.uses_llm && (
            <span className="inline-flex items-center gap-1 rounded-full bg-xanh-amber/15 text-xanh-amber text-[10px] font-mono px-2 py-0.5">
              <Zap className="h-3 w-3" /> LLM
            </span>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground mt-3 leading-relaxed">{a.description}</p>

      <div className="grid grid-cols-3 gap-2 mt-4">
        <div className="rounded-lg bg-muted/50 px-2 py-1.5">
          <div className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground">
            Lượt chạy
          </div>
          <div className="font-display text-lg font-bold text-foreground">{a.runs}</div>
        </div>
        <div className="rounded-lg bg-muted/50 px-2 py-1.5">
          <div className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground">
            Lỗi
          </div>
          <div
            className={`font-display text-lg font-bold ${
              healthy ? "text-foreground" : "text-red-500"
            }`}
          >
            {Math.round(a.error_rate * 100)}%
          </div>
        </div>
        <div className="rounded-lg bg-muted/50 px-2 py-1.5">
          <div className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground">
            Độ trễ
          </div>
          <div className="font-display text-lg font-bold text-foreground">
            {a.avg_latency_ms || "—"}
            {a.avg_latency_ms ? <span className="text-[10px] font-mono">ms</span> : null}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 mt-3 text-[11px] font-mono text-muted-foreground">
        <Clock className="h-3 w-3" />
        Gần nhất: {timeAgo(a.last_run)}
        {a.flag && (
          <span className="ml-auto truncate" title={a.flag}>
            {a.flag}
          </span>
        )}
      </div>
    </div>
  );
}

function AgentControlPage() {
  const { data: me } = useMe();
  const isAdmin = me?.role === "admin";
  const qc = useQueryClient();
  const [agentFilter, setAgentFilter] = useState<string>("");

  const stats = useQuery({
    queryKey: ["agent-stats"],
    queryFn: async () => {
      const json = await apiFetch<{ data: StatsData }>("/api/agent/stats?hours=24");
      return json.data;
    },
    refetchInterval: 30_000,
    retry: 1,
    enabled: isAdmin,
  });

  const aiLog = useQuery({
    queryKey: ["agent-ai-log", agentFilter],
    queryFn: async () => {
      const q = agentFilter ? `?limit=80&agent=${encodeURIComponent(agentFilter)}` : "?limit=80";
      const json = await apiFetch<{ data: AiLogEntry[] }>(`/api/agent/ai-log${q}`);
      return json.data;
    },
    refetchInterval: 30_000,
    retry: 1,
    enabled: isAdmin,
  });

  const runPipeline = useMutation({
    mutationFn: async () => {
      const json = await apiFetch<{ data: { duration_ms: number; alerts_created: number } }>(
        "/api/agent/run?hours=24",
        { method: "POST" }
      );
      return json.data;
    },
    onSuccess: (d) => {
      toast.success(
        `Pipeline chạy xong trong ${(d.duration_ms / 1000).toFixed(1)}s — ${d.alerts_created} ticket mới`
      );
      qc.invalidateQueries({ queryKey: ["agent-stats"] });
      qc.invalidateQueries({ queryKey: ["agent-ai-log"] });
    },
    onError: (e: Error) => toast.error(`Lỗi chạy pipeline: ${e.message}`),
  });

  const data = stats.data;

  if (me && !isAdmin) {
    return (
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Bot className="h-7 w-7 text-xanh-green" />
          Điều khiển Agent
        </h1>
        <div className="rounded-lg border border-dashed border-muted-foreground/30 bg-muted/20 px-6 py-12 text-center text-sm text-muted-foreground">
          Trang Điều khiển Agent chỉ dành cho quản trị viên (admin). Số liệu vận hành agent là
          dữ liệu toàn hệ thống, không phân tách theo phòng ban.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div
            className="h-11 w-11 rounded-2xl grid place-items-center text-white shadow-[var(--shadow-green)]"
            style={{ background: "var(--gradient-green)" }}
          >
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Điều khiển Agent</h1>
            <p className="text-sm text-muted-foreground">
              Giám sát & vận hành dây chuyền 6 agent nghiệp vụ
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              stats.refetch();
              aiLog.refetch();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-all active:scale-95"
          >
            <RefreshCw className={`h-4 w-4 ${stats.isFetching ? "animate-spin" : ""}`} />
            Làm mới
          </button>
          {isAdmin && (
            <button
              onClick={() => runPipeline.mutate()}
              disabled={runPipeline.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-600 transition-all active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed shadow-[var(--shadow-green)]"
            >
              {runPipeline.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Chạy pipeline ngay
            </button>
          )}
        </div>
      </div>

      {/* Worker status banner */}
      {data && (
        <div
          className={`rounded-2xl border p-4 flex flex-wrap items-center gap-x-8 gap-y-2 ${
            data.worker_enabled
              ? "border-emerald-500/30 bg-emerald-500/5"
              : "border-amber-500/30 bg-amber-500/5"
          }`}
        >
          <div className="flex items-center gap-2">
            <Activity
              className={`h-5 w-5 ${data.worker_enabled ? "text-emerald-500" : "text-amber-500"}`}
            />
            <span className="font-display font-semibold text-foreground">
              Agent-worker: {data.worker_enabled ? "Đang hoạt động" : "Đã tạm dừng"}
            </span>
          </div>
          <Stat label="Chu kỳ" value={`${Math.round(data.interval_seconds / 60)} phút`} />
          <Stat label="Tổng lượt chạy (24h)" value={String(data.total_runs)} />
          <Stat label="Cửa sổ dữ liệu" value={`${data.window_hours}h`} />
          {data.db_error && (
            <span className="inline-flex items-center gap-1.5 text-sm text-red-500">
              <AlertTriangle className="h-4 w-4" /> DB: {data.db_error}
            </span>
          )}
        </div>
      )}

      {/* Loading / error */}
      {stats.isLoading && (
        <div className="flex items-center justify-center min-h-[200px] text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      )}
      {stats.isError && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-4 text-red-500 text-sm">
          Không tải được thống kê agent: {(stats.error as Error)?.message}
        </div>
      )}

      {/* Agent grid */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.agents.map((a) => (
            <AgentCard key={a.name} a={a} />
          ))}
        </div>
      )}

      {/* AI Log viewer */}
      <div className="rounded-2xl border border-border bg-card/80 backdrop-blur-sm shadow-[var(--shadow-card)] overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-muted-foreground" />
            <h2 className="font-display font-semibold text-foreground">Nhật ký vận hành (ai-log)</h2>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Tất cả agent</option>
              {data?.agents.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="max-h-[420px] overflow-y-auto">
          {aiLog.isLoading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : !aiLog.data || aiLog.data.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              Chưa có log nào (file ai-log reset sau mỗi lần redeploy — log bền vững ở bảng
              agent_run_logs).
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card/95 backdrop-blur border-b border-border">
                <tr className="text-left text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-2 font-medium">Thời gian</th>
                  <th className="px-3 py-2 font-medium">Agent</th>
                  <th className="px-3 py-2 font-medium">Trạng thái</th>
                  <th className="px-3 py-2 font-medium text-right">Độ trễ</th>
                  <th className="px-5 py-2 font-medium">Tóm tắt</th>
                </tr>
              </thead>
              <tbody>
                {aiLog.data.map((e, i) => (
                  <tr
                    key={`${e.run_id}-${i}`}
                    className="border-b border-border/50 hover:bg-muted/40 transition-colors"
                  >
                    <td className="px-5 py-2 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      {timeAgo(e.ts)}
                    </td>
                    <td className="px-3 py-2 font-mono text-[11px] text-foreground">{e.agent}</td>
                    <td className={`px-3 py-2 font-mono text-[11px] font-semibold ${statusColor(e.status)}`}>
                      {e.status}
                    </td>
                    <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground text-right">
                      {e.latency_ms ? `${e.latency_ms}ms` : "—"}
                    </td>
                    <td className="px-5 py-2 text-[12px] text-muted-foreground max-w-md truncate">
                      {e.error ? <span className="text-red-500">{e.error}</span> : e.summary || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {!isAdmin && (
        <p className="text-xs text-muted-foreground text-center">
          Bạn đang xem ở chế độ giám sát. Chỉ quản trị viên mới chạy được pipeline thủ công.
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="font-display font-bold text-foreground">{value}</div>
    </div>
  );
}
