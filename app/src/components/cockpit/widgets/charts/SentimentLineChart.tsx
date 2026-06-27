import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import { Card, SectionHeader } from "../../primitives";
import { LineChart as LineChartIcon } from "lucide-react";

function shortDate(iso: string) {
  return iso.slice(5); // "MM-DD"
}

const LINES = [
  { key: "positive", label: "Tích cực", color: "var(--color-chart-2)", dash: undefined },
  { key: "neutral", label: "Trung tính", color: "var(--color-chart-1)", dash: "4 2" },
  { key: "negative", label: "Tiêu cực", color: "var(--color-chart-3)", dash: "3 3" },
] as const;

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card p-3 shadow-lg text-xs">
      <div className="font-mono font-semibold text-muted-foreground mb-2">{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center justify-between gap-4">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="font-mono font-semibold">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export function SentimentLineChart() {
  const { data: ov, isLoading } = useCockpitOverview();
  const chartData = (ov?.trend_sentiment ?? []).map((d) => ({
    ...d,
    date: shortDate(d.date),
  }));

  return (
    <Card>
      <SectionHeader
        icon={LineChartIcon}
        title="Xu hướng sentiment (14 ngày)"
        subtitle="Phân tách positive · neutral · negative theo ngày"
        right={
          <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground">
            {LINES.map((l) => (
              <span key={l.key} className="flex items-center gap-1">
                <span className="inline-block h-0.5 w-5 rounded" style={{ background: l.color }} />
                {l.label}
              </span>
            ))}
          </div>
        }
      />
      <div className="px-4 pb-4 pt-2">
        {isLoading ? (
          <div className="h-52 animate-pulse bg-muted/40 rounded-xl" />
        ) : chartData.length === 0 ? (
          <div className="h-52 flex items-center justify-center text-xs text-muted-foreground">Chưa có dữ liệu</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono", fill: "var(--color-muted-foreground)" }}
                interval={2}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono", fill: "var(--color-muted-foreground)" }}
                axisLine={false}
                tickLine={false}
                width={32}
              />
              <Tooltip content={<CustomTooltip />} />
              {LINES.map((l) => (
                <Line
                  key={l.key}
                  type="monotone"
                  dataKey={l.key}
                  name={l.label}
                  stroke={l.color}
                  strokeWidth={l.key === "neutral" ? 1.5 : 2}
                  strokeDasharray={l.dash}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
