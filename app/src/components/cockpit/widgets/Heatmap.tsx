import { Radar } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import { Card, SectionHeader } from "../primitives";
import { useCockpitFilter } from "../CockpitFilterContext";

function heatColor(v: number, maxVal: number) {
  if (maxVal === 0) return "oklch(0.95 0.02 160)";
  const ratio = v / maxVal;
  if (ratio < 0.25) return "oklch(0.95 0.05 160)";
  if (ratio < 0.5) return "oklch(0.85 0.1 160)";
  if (ratio < 0.75) return "oklch(0.72 0.16 145)";
  return "oklch(0.6 0.2 35)";
}

interface Props {
  onOpenDrawer?: (area: string) => void;
}

export function Heatmap({ onOpenDrawer }: Props) {
  const { data: ov } = useCockpitOverview();
  const { filter, setArea } = useCockpitFilter();
  const heatmap = ov?.heatmap;
  const loading = !ov;

  const areas = heatmap?.areas ?? [];
  const hours = heatmap?.hours ?? ["06", "09", "12", "15", "18", "21"];
  const cells = heatmap?.cells ?? [];

  const cellMap = new Map(cells.map((c) => [`${c.area}|${c.hour}`, c.negative_count]));
  const maxVal = cells.reduce((m, c) => Math.max(m, c.negative_count), 0);

  function handleClick(area: string) {
    setArea(filter.area === area ? null : area);
    onOpenDrawer?.(area);
  }

  return (
    <Card>
      <SectionHeader icon={Radar} title="Heatmap khu vực × giờ" subtitle="Click ô để lọc · mật độ tiêu cực" />
      <div className="px-4 pb-4">
        {loading ? (
          <div className="space-y-1 animate-pulse">
            {Array.from({ length: 4 }).map((_, rowIdx) => (
              <div key={rowIdx} className="flex items-center gap-1">
                <div className="w-20 h-5 bg-muted rounded" />
                {Array.from({ length: 6 }).map((_, colIdx) => (
                  <div key={colIdx} className="flex-1 h-6 bg-muted rounded" />
                ))}
              </div>
            ))}
          </div>
        ) : areas.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground">Chưa có dữ liệu heatmap</div>
        ) : (
          <>
            <div className="flex gap-1 pl-20 mb-1">
              {hours.map((h) => (
                <div key={h} className="flex-1 text-center text-[10px] font-mono text-muted-foreground">{h}h</div>
              ))}
            </div>
            {areas.map((area) => (
              <div key={area} className="flex items-center gap-1 mb-1">
                <span
                  className={`w-20 text-[10px] font-mono truncate cursor-pointer transition-colors ${filter.area === area ? "text-xanh-deep font-semibold" : "text-muted-foreground hover:text-foreground"}`}
                  title={area}
                  onClick={() => handleClick(area)}
                >
                  {area}
                </span>
                {hours.map((h) => {
                  const v = cellMap.get(`${area}|${h}`) ?? 0;
                  return (
                    <div
                      key={h}
                      title={`${area} · ${h}h · ${v} tiêu cực`}
                      className="flex-1 h-6 rounded cursor-pointer hover:opacity-80 transition-opacity"
                      style={{
                        background: heatColor(v, maxVal),
                        outline: filter.area === area ? "2px solid var(--xanh-deep)" : "none",
                      }}
                      onClick={() => handleClick(area)}
                    />
                  );
                })}
              </div>
            ))}
          </>
        )}
      </div>
    </Card>
  );
}
