import { MapPin } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import { Card, SectionHeader } from "../primitives";

export function DriverWatchlist() {
  const { data: ov } = useCockpitOverview();
  const cells = ov?.heatmap?.cells ?? [];

  // Gộp theo area, tổng negative_count → top 5 khu vực rủi ro cao nhất.
  const areaMap = new Map<string, number>();
  for (const c of cells) {
    areaMap.set(c.area, (areaMap.get(c.area) ?? 0) + c.negative_count);
  }
  const sorted = [...areaMap.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);

  return (
    <Card>
      <SectionHeader icon={MapPin} title="Khu vực rủi ro" subtitle="Mật độ phản hồi tiêu cực · 14 ngày" />
      <div className="px-3 pb-3 space-y-2">
        {!ov ? (
          <div className="space-y-2 animate-pulse">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-border bg-card p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-5 bg-muted rounded" />
                    <div className="h-3.5 bg-muted rounded w-24" />
                  </div>
                  <div className="h-3.5 bg-muted rounded w-16" />
                </div>
              </div>
            ))}
          </div>
        ) : sorted.length === 0 ? (
          <div className="py-6 text-center text-xs text-muted-foreground">Chưa có dữ liệu khu vực</div>
        ) : (
          sorted.map(([area, count], idx) => (
            <div key={area} className="flex items-center justify-between rounded-xl border border-border bg-card p-3">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-muted-foreground">#{idx + 1}</span>
                <div className="font-mono text-sm font-semibold text-xanh-deep">{area}</div>
              </div>
              <div className="text-sm font-semibold text-xanh-coral">{count} tiêu cực</div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
