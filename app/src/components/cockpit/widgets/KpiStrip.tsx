import { ClipboardList, Eye, MessageSquare, Siren, TrendingUp, Workflow } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";

function fmt(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function deltaPct(pct: number | null | undefined) {
  if (pct == null) return "—";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function KpiStrip() {
  const { data: ov } = useCockpitOverview();
  const k = ov?.kpis;

  const items = [
    {
      label: "Feedback hôm nay",
      value: k ? fmt(k.feedback_today) : "—",
      delta: k ? deltaPct(k.feedback_today_delta_pct) : "...",
      icon: MessageSquare,
      tone: "green",
    },
    {
      label: "Negative rate",
      value: k ? `${k.negative_rate.toFixed(1)}%` : "—",
      delta: k ? `hôm nay ${k.negative_rate_today.toFixed(1)}%` : "...",
      icon: TrendingUp,
      tone: "green",
    },
    {
      label: "Cần review",
      value: k ? fmt(k.needs_review) : "—",
      delta: "human-in-loop",
      icon: Eye,
      tone: "cyan",
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
    },
    {
      label: "Alerts mở",
      value: k?.alerts_open != null ? fmt(k.alerts_open) : "—",
      delta: "spike & pattern",
      icon: Siren,
      tone: "amber",
    },
    {
      label: "Correction log",
      value: k?.corrections_7d != null ? fmt(k.corrections_7d) : "—",
      delta: "7 ngày",
      icon: Workflow,
      tone: "green",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {items.map((i) => {
        const Icon = i.icon;
        const toneCls =
          i.tone === "amber"
            ? "text-xanh-amber"
            : i.tone === "cyan"
              ? "text-xanh-cyan"
              : i.tone === "deep"
                ? "text-xanh-deep"
                : "text-xanh-green";
        return (
          <div
            key={i.label}
            className="rounded-xl border border-border bg-white p-3 shadow-[var(--shadow-card)]"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground">{i.label}</span>
              <Icon className={`h-3.5 w-3.5 ${toneCls}`} />
            </div>
            <div className="mt-1 font-display text-xl font-bold text-xanh-deep">{i.value}</div>
            <div className="text-[10px] font-mono text-muted-foreground">{i.delta}</div>
          </div>
        );
      })}
    </div>
  );
}
