import { Funnel, FunnelChart, LabelList, ResponsiveContainer, Tooltip } from "recharts";
import { Filter } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import type { FunnelData } from "../../types";
import { Card, SectionHeader } from "../../primitives";

const STAGES = [
  { key: "total" as const, label: "Tổng feedback", color: "oklch(0.38 0.08 240)" },
  { key: "classified" as const, label: "Đã phân loại", color: "var(--xanh-cyan)" },
  { key: "needs_review" as const, label: "Cần review", color: "var(--xanh-amber)" },
  { key: "alerts_triggered" as const, label: "Sinh alert", color: "oklch(0.62 0.2 35)" },
  { key: "tickets_created" as const, label: "Tạo ticket", color: "var(--xanh-coral)" },
  { key: "resolved" as const, label: "Đã giải quyết", color: "var(--xanh-green)" },
];

function buildFunnelData(funnel: FunnelData) {
  const total = funnel.total || 1;
  return STAGES.map((s) => ({
    name: s.label,
    value: funnel[s.key],
    pct: Math.round((funnel[s.key] / total) * 100),
    fill: s.color,
  }));
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { name: string; value: number; pct: number } }>;
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl border border-border bg-card p-3 shadow-lg text-xs">
      <div className="font-semibold">{d.name}</div>
      <div className="font-mono mt-1">{d.value.toLocaleString()} · {d.pct}% của tổng</div>
    </div>
  );
}

export function PipelineFunnel() {
  const { data: ov, isLoading } = useCockpitOverview();
  const funnel = ov?.funnel as FunnelData | undefined;
  const isEmpty = !funnel || !("total" in funnel) || funnel.total === 0;

  return (
    <Card>
      <SectionHeader
        icon={Filter}
        title="Pipeline xử lý"
        subtitle="Từ feedback đến giải quyết · tỷ lệ qua từng bước"
      />
      <div className="px-4 pb-4 pt-2">
        {isLoading ? (
          <div className="h-64 animate-pulse bg-muted/40 rounded-xl" />
        ) : isEmpty ? (
          <div className="h-64 flex flex-col items-center justify-center text-xs text-muted-foreground gap-2">
            <Filter className="h-6 w-6 opacity-30" />
            <span>Chưa có dữ liệu pipeline</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <FunnelChart>
              <Tooltip content={<CustomTooltip />} />
              <Funnel
                dataKey="value"
                data={buildFunnelData(funnel)}
                isAnimationActive
              >
                <LabelList
                  position="right"
                  fill="oklch(0.4 0.04 200)"
                  stroke="none"
                  dataKey="name"
                  style={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
                />
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
