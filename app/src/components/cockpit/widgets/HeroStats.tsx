import { Brain, Gauge, MessageSquare, Zap } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";

export function HeroStats() {
  const { data: ov } = useCockpitOverview();
  const k = ov?.kpis;

  const stats = [
    {
      label: "Feedback / cửa sổ",
      value: k ? (k.window_total >= 1000 ? `${(k.window_total / 1000).toFixed(1)}k` : String(k.window_total)) : "—",
      sub: `${ov?.window_days ?? 14} ngày gần nhất`,
      icon: MessageSquare,
    },
    {
      label: "Negative rate",
      value: k ? `${k.negative_rate.toFixed(1)}%` : "—",
      sub: `hôm nay ${k ? k.negative_rate_today.toFixed(1) : "—"}%`,
      icon: Brain,
    },
    {
      label: "Cần review",
      value: k ? String(k.needs_review) : "—",
      sub: "human-in-loop",
      icon: Zap,
    },
    {
      label: "Alerts mở",
      value: k?.alerts_open != null ? String(k.alerts_open) : "—",
      sub: "spike & anomaly",
      icon: Gauge,
    },
  ];

  return (
    <div className="rounded-2xl p-5 border border-border bg-white/80 backdrop-blur shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-mono text-muted-foreground">QUALITY · SNAPSHOT</div>
        <span className="text-[10px] font-mono text-xanh-deep bg-xanh-mint px-2 py-0.5 rounded-full">14 ngày</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="rounded-xl p-3 border border-border bg-gradient-to-br from-white to-xanh-mint/30">
              <Icon className="h-4 w-4 text-xanh-green" />
              <div className="mt-2 font-display text-2xl font-bold text-xanh-deep">{s.value}</div>
              <div className="text-[11px] text-muted-foreground">{s.label}</div>
              <div className="text-[10px] font-mono text-xanh-green mt-0.5">{s.sub}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
