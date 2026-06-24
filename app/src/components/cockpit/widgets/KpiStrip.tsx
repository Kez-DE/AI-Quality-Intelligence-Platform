import { ClipboardList, Eye, MessageSquare, RefreshCw, Siren, TrendingUp, Workflow } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";

function fmt(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function deltaPct(pct: number | null | undefined) {
  if (pct == null) return "—";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

const KPI_TOOLTIPS: Record<string, string> = {
  "Feedback hôm nay": "Tổng feedback khách hàng nhận được trong ngày hôm nay",
  "Negative rate": "Tỷ lệ phần trăm feedback tiêu cực trên tổng feedback (7 ngày)",
  "Cần review": "Feedback chờ xem xét thủ công — human-in-loop",
  "Open tickets": "Số ticket CSKH đang mở chưa được xử lý",
  "Alerts mở": "Cảnh báo tự động từ hệ thống chưa được resolve",
  "Correction log": "Số lần AI bị người dùng override trong 7 ngày qua",
};

function KpiSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-3 shadow-[var(--shadow-card)] animate-pulse">
          <div className="flex items-center justify-between mb-3">
            <div className="h-2.5 bg-muted rounded w-3/4" />
            <div className="h-3.5 w-3.5 bg-muted rounded" />
          </div>
          <div className="h-6 bg-muted rounded w-1/2 mb-2" />
          <div className="h-2.5 bg-muted rounded w-2/3" />
        </div>
      ))}
    </div>
  );
}

export function KpiStrip() {
  const { data: ov, isLoading, isError, refetch } = useCockpitOverview();

  if (isLoading) return <KpiSkeleton />;

  if (isError) {
    return (
      <div className="rounded-xl border border-border bg-card px-4 py-5 text-center text-sm text-muted-foreground">
        Không tải được KPI.{" "}
        <button
          onClick={() => refetch()}
          className="text-xanh-green underline-offset-2 hover:underline inline-flex items-center gap-1"
        >
          <RefreshCw className="h-3 w-3" /> Thử lại
        </button>
      </div>
    );
  }

  const k = ov?.kpis;
  const hasAlerts = (k?.alerts_open ?? 0) > 0;
  const isHighNegative = (k?.negative_rate ?? 0) > 30;

  const items = [
    {
      label: "Feedback hôm nay",
      value: k ? fmt(k.feedback_today) : "—",
      delta: k ? deltaPct(k.feedback_today_delta_pct) : "...",
      icon: MessageSquare,
      tone: "cyan",
      urgent: false,
    },
    {
      label: "Negative rate",
      value: k ? `${k.negative_rate.toFixed(1)}%` : "—",
      delta: k ? `hôm nay ${k.negative_rate_today.toFixed(1)}%` : "...",
      icon: TrendingUp,
      tone: "coral",
      urgent: isHighNegative,
    },
    {
      label: "Cần review",
      value: k ? fmt(k.needs_review) : "—",
      delta: "chờ xét duyệt thủ công",
      icon: Eye,
      tone: "cyan",
      urgent: false,
    },
    {
      label: "Open tickets",
      value: k?.tickets_open != null ? fmt(k.tickets_open) : "—",
      delta: k?.tickets_by_priority
        ? Object.entries(k.tickets_by_priority)
            .sort(([a], [b]) => b.localeCompare(a))
            .slice(0, 2)
            .map(([p, n]) => `${p}: ${n}`)
            .join(" · ")
        : "—",
      icon: ClipboardList,
      tone: "deep",
      urgent: false,
    },
    {
      label: "Alerts mở",
      value: k?.alerts_open != null ? fmt(k.alerts_open) : "—",
      delta: "spike & pattern",
      icon: Siren,
      tone: "amber",
      urgent: hasAlerts,
    },
    {
      label: "Correction log",
      value: k?.corrections_7d != null ? fmt(k.corrections_7d) : "—",
      delta: "7 ngày",
      icon: Workflow,
      tone: "green",
      urgent: false,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {items.map((i) => {
        const Icon = i.icon;
        const toneCls =
          i.tone === "amber"
            ? "text-xanh-amber"
            : i.tone === "coral"
              ? "text-xanh-coral"
              : i.tone === "cyan"
                ? "text-xanh-cyan"
                : i.tone === "deep"
                  ? "text-xanh-deep"
                  : "text-xanh-green";
        return (
          <div
            key={i.label}
            className={`rounded-xl border bg-card p-3 shadow-[var(--shadow-card)] transition-colors ${
              i.urgent
                ? "border-xanh-coral/50 ring-1 ring-inset ring-xanh-coral/20 bg-xanh-coral/[0.03]"
                : "border-border"
            }`}
          >
            <div className="flex items-center justify-between">
              <span
                className="text-xs text-muted-foreground"
                title={KPI_TOOLTIPS[i.label]}
              >
                {i.label}
              </span>
              <Icon className={`h-3.5 w-3.5 ${toneCls}`} />
            </div>
            <div className="mt-1 font-display text-xl font-bold text-xanh-deep">{i.value}</div>
            <div className="text-xs font-mono text-muted-foreground">{i.delta}</div>
          </div>
        );
      })}
    </div>
  );
}
