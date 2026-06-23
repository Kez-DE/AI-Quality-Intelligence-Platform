import { BarChart3, Car, Cpu, Layers, Shield, Tag, Users } from "lucide-react";
import type { LucideProps } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import type { CategorySlice } from "../types";
import { Card, SectionHeader } from "../primitives";
import { useCockpitFilter } from "../CockpitFilterContext";

const TOPIC_META: Record<string, { color: string; icon: React.ComponentType<LucideProps> }> = {
  "Tài xế": { color: "var(--xanh-green)", icon: Users },
  "Driver Attitude": { color: "var(--xanh-green)", icon: Users },
  "Xe / phương tiện": { color: "var(--xanh-cyan)", icon: Car },
  "Vehicle Issue": { color: "var(--xanh-cyan)", icon: Car },
  "Ứng dụng": { color: "var(--xanh-deep)", icon: Cpu },
  "App Issue": { color: "var(--xanh-deep)", icon: Cpu },
  "Giá & thanh toán": { color: "var(--xanh-amber)", icon: Tag },
  "Payment Issue": { color: "var(--xanh-amber)", icon: Tag },
  "An toàn": { color: "var(--xanh-coral)", icon: Shield },
  "Safety": { color: "var(--xanh-coral)", icon: Shield },
};

function meta(topic: string) {
  return TOPIC_META[topic] ?? { color: "oklch(0.6 0.02 180)", icon: Layers };
}

interface Props {
  onOpenDrawer?: (topic: string) => void;
}

export function CategoryBreakdown({ onOpenDrawer }: Props) {
  const { data: ov } = useCockpitOverview();
  const { filter, setTopic } = useCockpitFilter();
  const cats: CategorySlice[] = ov?.categories ?? [];
  const loading = !ov;

  function handleClick(topic: string) {
    setTopic(filter.topic === topic ? null : topic);
    onOpenDrawer?.(topic);
  }

  return (
    <Card>
      <SectionHeader icon={BarChart3} title="Phân loại theo chủ đề" subtitle="Click để lọc" />
      <div className="px-5 pb-5 space-y-3">
        {loading ? (
          <div className="py-8 text-center text-xs text-muted-foreground">Loading...</div>
        ) : cats.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground">Chưa có dữ liệu phân loại</div>
        ) : (
          cats.map((c) => {
            const { color, icon: Icon } = meta(c.topic);
            const active = filter.topic === c.topic;
            return (
              <div
                key={c.topic}
                onClick={() => handleClick(c.topic)}
                className={`cursor-pointer rounded-lg px-2 py-1 -mx-2 transition-colors ${active ? "bg-xanh-mint/50" : "hover:bg-muted/50"}`}
              >
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="flex items-center gap-2">
                    <Icon className="h-3.5 w-3.5" style={{ color }} />
                    <span className={`font-medium ${active ? "text-xanh-deep font-semibold" : ""}`}>{c.topic}</span>
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">{c.pct.toFixed(1)}%</span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(c.pct, 100)}%`, background: color }} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
