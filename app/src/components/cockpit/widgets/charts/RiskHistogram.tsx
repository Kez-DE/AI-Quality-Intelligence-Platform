import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import { Card, SectionHeader } from "../../primitives";

function barColor(score: number) {
  if (score <= 3) return "var(--color-chart-2)"; // rủi ro thấp · teal-green
  if (score <= 6) return "var(--color-chart-1)"; // trung bình · cyan
  if (score <= 8) return "var(--color-chart-4)"; // nâng cao · amber
  return "var(--color-chart-3)"; // cao · coral
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card p-3 shadow-lg text-xs font-mono">
      <div className="text-muted-foreground">Risk score {label}</div>
      <div className="font-semibold mt-0.5">{payload[0].value} phản hồi</div>
    </div>
  );
}

export function RiskHistogram() {
  const { data: ov, isLoading } = useCockpitOverview();
  const dist = ov?.risk_distribution ?? [];

  const chartData = dist.map((d) => ({
    score: `R${d.score}`,
    count: d.count,
    scoreNum: d.score,
  }));

  return (
    <Card>
      <SectionHeader
        icon={Activity}
        title="Phân phối rủi ro"
        subtitle="Overall risk score 1–10 · số phản hồi theo mức"
      />
      <div className="px-4 pb-4 pt-2">
        {isLoading ? (
          <div className="h-64 animate-pulse bg-muted/40 rounded-xl" />
        ) : dist.every((d) => d.count === 0) ? (
          <div className="h-64 flex items-center justify-center text-xs text-muted-foreground">Chưa có dữ liệu rủi ro</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 4, right: 40, left: 8, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono", fill: "var(--color-muted-foreground)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="score"
                width={28}
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono", fill: "var(--color-muted-foreground)" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "var(--color-muted)" }} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={20}>
                {chartData.map((entry) => (
                  <Cell key={entry.score} fill={barColor(entry.scoreNum)} />
                ))}
                <LabelList
                  dataKey="count"
                  position="right"
                  style={{ fontSize: 10, fontFamily: "JetBrains Mono", fill: "var(--color-muted-foreground)" }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
