import { LineChart as LineChartIcon } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import type { TrendPoint } from "../types";
import { Card, Legend, SectionHeader } from "../primitives";

function buildPath(arr: number[], max: number, w: number, h: number) {
  const stepX = w / Math.max(arr.length - 1, 1);
  return arr.map((v, i) => `${i === 0 ? "M" : "L"} ${i * stepX} ${h - (v / max) * h}`).join(" ");
}

export function TrendCard() {
  const { data: ov } = useCockpitOverview();
  const trend: TrendPoint[] = ov?.trend ?? [];

  const totals = trend.map((t) => t.total);
  const negatives = trend.map((t) => t.negative);
  const max = Math.max(...totals, 1);
  const w = 600;
  const h = 180;
  const stepX = w / Math.max(trend.length - 1, 1);

  // Tìm ngày có negative cao nhất cho spike marker.
  const spikeIdx = negatives.indexOf(Math.max(...negatives, 0));
  const spikeDate = trend[spikeIdx]?.date ?? "";

  const loading = !ov;

  return (
    <Card>
      <SectionHeader
        icon={LineChartIcon}
        title="Xu hướng phản hồi (14 ngày)"
        subtitle="Tổng phản hồi · Phản hồi tiêu cực · Spike"
        right={
          <div className="flex items-center gap-3 text-[11px] font-mono">
            <Legend color="var(--color-chart-1)" label="tổng" />
            <Legend color="var(--color-chart-3)" label="tiêu cực" />
          </div>
        }
      />
      <div className="px-5 pb-5">
        {loading ? (
          <div className="w-full h-44 rounded-lg bg-muted/50 animate-pulse relative overflow-hidden">
            {[0.25, 0.5, 0.75].map((p) => (
              <div key={p} className="absolute w-full border-t border-border/40" style={{ top: `${p * 100}%` }} />
            ))}
          </div>
        ) : trend.length === 0 ? (
          <div className="w-full h-44 flex items-center justify-center text-xs text-muted-foreground font-mono">Chưa có dữ liệu xu hướng</div>
        ) : (
          <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-44">
            <defs>
              <linearGradient id="gTotal" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity="0.4" />
                <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity="0" />
              </linearGradient>
            </defs>
            {[0.25, 0.5, 0.75].map((p) => (
              <line key={p} x1="0" x2={w} y1={h * p} y2={h * p} stroke="var(--color-border)" strokeDasharray="3 3" />
            ))}
            <path d={`${buildPath(totals, max, w, h)} L ${w} ${h} L 0 ${h} Z`} fill="url(#gTotal)" />
            <path d={buildPath(totals, max, w, h)} fill="none" stroke="var(--color-chart-1)" strokeWidth="2.5" />
            <path d={buildPath(negatives, max, w, h)} fill="none" stroke="var(--color-chart-3)" strokeWidth="2" strokeDasharray="3 3" />
            {spikeIdx >= 0 && negatives[spikeIdx] > 0 && (
              <>
                <circle cx={spikeIdx * stepX} cy={h - (negatives[spikeIdx] / max) * h} r="6" fill="var(--color-chart-3)" />
                <text x={spikeIdx * stepX + 10} y={h - (negatives[spikeIdx] / max) * h - 4} fontSize="10" fill="var(--color-chart-3)" fontFamily="JetBrains Mono">
                  spike · {spikeDate.slice(5)}
                </text>
              </>
            )}
          </svg>
        )}
      </div>
    </Card>
  );
}
