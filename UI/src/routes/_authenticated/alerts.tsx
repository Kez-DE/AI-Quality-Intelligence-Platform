import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Headphones,
  Loader2,
  MapPin,
  RefreshCw,
  Shield,
  Siren,
  Truck,
  Users,
  Wrench,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/alerts")({
  component: AlertsPage,
});

// ---- Types ----
type Alert = {
  id: string;
  title: string;
  description: string;
  severity: string;
  area: string | null;
  status: string;
  created_at: string;
  user_id: string;
};

// Phân tích "assigned_team" từ description (field được nhét vào description dạng "...\\n\\n**Action Plan:** ...\\n**Assigned Team:** ...")
function parseDescription(raw: string): {
  description: string;
  action: string;
  assigned_team: string;
} {
  const actionMatch = raw.match(/\*\*Action Plan:\*\*\s*(.*)/);
  const teamMatch = raw.match(/\*\*Assigned Team:\*\*\s*(.*)/);
  const descClean = raw.split("\n\n**Action Plan:**")[0].trim();
  return {
    description: descClean,
    action: actionMatch?.[1]?.trim() ?? "",
    assigned_team: teamMatch?.[1]?.trim() ?? "Vận Hành",
  };
}

// Map team sang icon + màu
const TEAM_CONFIG: Record<
  string,
  { label: string; icon: React.ComponentType<{ className?: string }>; color: string; bg: string }
> = {
  "Vận Hành": { label: "Vận Hành", icon: Wrench, color: "text-blue-700", bg: "bg-blue-50 border-blue-200" },
  "CSKH": { label: "CSKH", icon: Headphones, color: "text-purple-700", bg: "bg-purple-50 border-purple-200" },
  "Safety": { label: "Safety", icon: Shield, color: "text-red-700", bg: "bg-red-50 border-red-200" },
  "IT": { label: "IT", icon: Zap, color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-200" },
  "Giao Hàng": { label: "Giao Hàng", icon: Truck, color: "text-orange-700", bg: "bg-orange-50 border-orange-200" },
  "Driver Mgmt": { label: "Driver Mgmt", icon: Users, color: "text-teal-700", bg: "bg-teal-50 border-teal-200" },
};

function getTeamConfig(team: string) {
  for (const key of Object.keys(TEAM_CONFIG)) {
    if (team.toLowerCase().includes(key.toLowerCase())) return TEAM_CONFIG[key];
  }
  return TEAM_CONFIG["Vận Hành"];
}

const TABS = ["Tất cả", "Vận Hành", "CSKH", "Safety", "IT", "Driver Mgmt"];
const API_BASE = import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000";

type LiveStreamStatus = {
  running: boolean;
  auto_ticket: boolean;
  ticket_running: boolean;
  batches_ingested: number;
  ticket_every_batches: number;
  last_ticket_at: string | null;
  last_ticket_batch: number | null;
  last_ticket_error: string | null;
  last_ticket_result: {
    spikes_detected?: number;
    alerts_created?: number;
  } | null;
};

type TicketWorkflowStatus = {
  enabled: boolean;
  in_progress_after_seconds: number;
  resolved_after_seconds: number;
  last_run_at: string | null;
  moved_to_in_progress: number;
  moved_to_resolved: number;
  last_error: string | null;
};

function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("Tất cả");
  const [stream, setStream] = useState<LiveStreamStatus | null>(null);
  const [workflow, setWorkflow] = useState<TicketWorkflowStatus | null>(null);

  async function fetchAlerts(showLoading = false) {
    if (showLoading) setLoading(true);
    try {
      const [alertsRes, statusRes, workflowRes] = await Promise.all([
        fetch(`${API_BASE}/api/alerts/recent?limit=100`),
        fetch(`${API_BASE}/api/live-stream/status`),
        fetch(`${API_BASE}/api/alerts/workflow-status`),
      ]);
      if (!alertsRes.ok || !statusRes.ok || !workflowRes.ok) throw new Error("Backend unavailable");
      const alertsJson = (await alertsRes.json()) as { data?: Alert[] };
      const statusJson = (await statusRes.json()) as { data?: LiveStreamStatus };
      const workflowJson = (await workflowRes.json()) as { data?: TicketWorkflowStatus };
      setAlerts(alertsJson.data ?? []);
      setStream(statusJson.data ?? null);
      setWorkflow(workflowJson.data ?? null);
    } catch {
      toast.error("Không đọc được trạng thái auto-ticket từ backend");
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  useEffect(() => {
    fetchAlerts(true);
    const polling = window.setInterval(() => fetchAlerts(), 2000);
    // Realtime subscription
    const channel = supabase
      .channel("alerts-realtime")
      .on("postgres_changes", { event: "*", schema: "public", table: "alerts" }, () => fetchAlerts())
      .subscribe();
    return () => {
      window.clearInterval(polling);
      supabase.removeChannel(channel);
    };
  }, []);

  async function updateStatus(id: string, newStatus: string) {
    setUpdating(id);
    try {
      const response = await fetch(`${API_BASE}/api/alerts/${id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      toast.success(newStatus === "in_progress" ? "✅ Đã nhận xử lý!" : "🎉 Đã đánh dấu hoàn thành!");
      fetchAlerts();
    } catch (error) {
      toast.error("Cập nhật thất bại: " + (error instanceof Error ? error.message : "Unknown error"));
    }
    setUpdating(null);
  }

  // Filter theo tab
  const filtered = alerts.filter((a) => {
    if (activeTab === "Tất cả") return true;
    const { assigned_team } = parseDescription(a.description ?? "");
    return assigned_team.toLowerCase().includes(activeTab.toLowerCase());
  });

  // Thống kê nhanh
  const openCount = alerts.filter((a) => a.status === "open").length;
  const inProgressCount = alerts.filter((a) => a.status === "in_progress").length;
  const resolvedCount = alerts.filter((a) => a.status === "resolved").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-2">
            <Siren className="h-7 w-7 text-xanh-coral" />
            Ticket Triage
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Cảnh báo AI tự động phân loại và giao về đúng phòng ban.
          </p>
        </div>
        <button
          onClick={() => fetchAlerts(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-border bg-white text-sm hover:bg-muted/50 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Làm mới
        </button>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center">
          <div className="font-display text-3xl font-bold text-red-600">{openCount}</div>
          <div className="text-sm text-red-700 font-medium mt-1">🔴 Chờ xử lý</div>
        </div>
        <div className="rounded-xl border-2 border-yellow-200 bg-yellow-50 p-4 text-center">
          <div className="font-display text-3xl font-bold text-yellow-600">{inProgressCount}</div>
          <div className="text-sm text-yellow-700 font-medium mt-1">🟡 Đang xử lý</div>
        </div>
        <div className="rounded-xl border-2 border-green-200 bg-green-50 p-4 text-center">
          <div className="font-display text-3xl font-bold text-green-600">{resolvedCount}</div>
          <div className="text-sm text-green-700 font-medium mt-1">🟢 Đã xong</div>
        </div>
      </div>

      <div className="border border-border bg-white px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <span className="inline-flex items-center gap-2 font-semibold">
          <span className={`h-2 w-2 rounded-full ${stream?.running ? "bg-xanh-green animate-pulse" : "bg-muted-foreground"}`} />
          {stream?.running ? "Live stream đang chạy" : "Live stream đã dừng"}
        </span>
        <span className="text-muted-foreground">Batch: <strong className="text-foreground">{stream?.batches_ingested ?? 0}</strong></span>
        <span className="text-muted-foreground">
          Auto-ticket: <strong className="text-foreground">
            {stream?.ticket_running
              ? "đang phân tích"
              : stream?.auto_ticket
                ? `mỗi ${stream.ticket_every_batches} batch`
                : "đã tắt"}
          </strong>
        </span>
        {stream?.last_ticket_at && (
          <span className="text-muted-foreground">
            Lần gần nhất: <strong className="text-foreground">batch {stream.last_ticket_batch}</strong>
            {` · ${stream.last_ticket_result?.alerts_created ?? 0} ticket`}
          </span>
        )}
        {stream?.last_ticket_error && (
          <span className="text-red-600">Lỗi trigger: {stream.last_ticket_error}</span>
        )}
        <span className="text-muted-foreground">
          Workflow: <strong className="text-foreground">
            {workflow?.enabled
              ? `chờ ${workflow.in_progress_after_seconds}s → xử lý → xong ${workflow.resolved_after_seconds}s`
              : "đã tắt"}
          </strong>
        </span>
        {workflow?.last_error && <span className="text-red-600">Lỗi workflow: {workflow.last_error}</span>}
      </div>

      {/* Tab Filter theo Phòng Ban */}
      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => {
          const cfg = tab !== "Tất cả" ? getTeamConfig(tab) : null;
          const Icon = cfg?.icon;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium border transition-all ${
                activeTab === tab
                  ? "border-xanh-green bg-xanh-deep text-white shadow"
                  : "border-border bg-white text-muted-foreground hover:border-xanh-green/40"
              }`}
            >
              {Icon && <Icon className="h-3.5 w-3.5" />}
              {tab}
            </button>
          );
        })}
      </div>

      {/* Alert Cards */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
          <span className="ml-3 text-muted-foreground">Đang tải dữ liệu từ Supabase...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <CheckCircle2 className="h-12 w-12 mx-auto text-xanh-green mb-3" />
          <p className="font-semibold">Không có ticket nào</p>
          <p className="text-sm mt-1">Chạy spike_detector.py để AI sinh ticket tự động.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((alert) => {
            const { description, action, assigned_team } = parseDescription(alert.description ?? "");
            const teamCfg = getTeamConfig(assigned_team);
            const TeamIcon = teamCfg.icon;
            const isUpdating = updating === alert.id;

            const statusColor =
              alert.status === "resolved"
                ? "border-green-300 bg-green-50"
                : alert.status === "in_progress"
                ? "border-yellow-300 bg-yellow-50"
                : "border-red-300 bg-white";

            const statusBadge =
              alert.status === "resolved"
                ? { label: "Đã giải quyết", cls: "bg-green-100 text-green-700" }
                : alert.status === "in_progress"
                ? { label: "Đang xử lý", cls: "bg-yellow-100 text-yellow-700" }
                : { label: "Chờ xử lý", cls: "bg-red-100 text-red-700" };

            return (
              <div
                key={alert.id}
                className={`rounded-2xl border-2 p-5 shadow-sm transition-all hover:shadow-md ${statusColor}`}
              >
                {/* Top row */}
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1">
                    {/* Severity badge */}
                    <span
                      className={`shrink-0 px-2 py-1 rounded-lg text-xs font-mono font-bold ${
                        alert.severity === "P1" || alert.severity === "P0"
                          ? "bg-red-600 text-white"
                          : "bg-yellow-400 text-yellow-900"
                      }`}
                    >
                      {alert.severity}
                    </span>
                    <div>
                      <h3 className="font-display font-bold text-base leading-snug">{alert.title}</h3>
                      <div className="flex flex-wrap gap-2 mt-1.5">
                        {/* Team badge */}
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${teamCfg.bg} ${teamCfg.color}`}
                        >
                          <TeamIcon className="h-3 w-3" />
                          {assigned_team}
                        </span>
                        {/* Area */}
                        {alert.area && (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                            <MapPin className="h-3 w-3" />
                            {alert.area}
                          </span>
                        )}
                        {/* Status */}
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge.cls}`}>
                          {statusBadge.label}
                        </span>
                        {/* Time */}
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {new Date(alert.created_at).toLocaleString("vi-VN")}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 shrink-0">
                    {alert.status === "open" && (
                      <button
                        onClick={() => updateStatus(alert.id, "in_progress")}
                        disabled={isUpdating}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-yellow-500 text-white text-xs font-semibold hover:bg-yellow-600 disabled:opacity-60 transition-colors"
                      >
                        {isUpdating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                        Nhận xử lý
                      </button>
                    )}
                    {alert.status === "in_progress" && (
                      <button
                        onClick={() => updateStatus(alert.id, "resolved")}
                        disabled={isUpdating}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-600 text-white text-xs font-semibold hover:bg-green-700 disabled:opacity-60 transition-colors"
                      >
                        {isUpdating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                        Đã giải quyết
                      </button>
                    )}
                    {alert.status === "resolved" && (
                      <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-100 text-green-700 text-xs font-semibold">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Hoàn thành
                      </span>
                    )}
                  </div>
                </div>

                {/* Description & Action */}
                <div className="mt-4 grid sm:grid-cols-2 gap-3">
                  <div className="rounded-xl bg-white/70 border border-border/60 p-3">
                    <div className="text-[10px] font-mono text-muted-foreground mb-1 uppercase">
                      🔍 Nguyên nhân gốc rễ (AI phân tích)
                    </div>
                    <p className="text-sm text-foreground leading-relaxed">{description}</p>
                  </div>
                  {action && (
                    <div className="rounded-xl bg-white/70 border border-border/60 p-3">
                      <div className="text-[10px] font-mono text-muted-foreground mb-1 uppercase">
                        ⚡ Hành động đề xuất
                      </div>
                      <p className="text-sm text-foreground leading-relaxed">{action}</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
