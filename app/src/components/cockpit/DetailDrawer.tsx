import { useQuery } from "@tanstack/react-query";
import { MapPin, X } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { apiFetch } from "@/lib/api";
import type { Database as DatabaseSchema } from "@/integrations/supabase/types";
import { Pill } from "./primitives";

type FeedRow = DatabaseSchema["public"]["Tables"]["feedback"]["Row"];

export interface DrawerFilter {
  topic?: string;
  area?: string;
  severity?: string;
  title: string;
}

interface Props {
  filter: DrawerFilter | null;
  onClose: () => void;
}

export function DetailDrawer({ filter, onClose }: Props) {
  const open = !!filter;

  const { data, isLoading } = useQuery({
    queryKey: ["cockpit-detail", filter],
    queryFn: async () => {
      if (!filter) return [];
      const params = new URLSearchParams({ limit: "20" });
      if (filter.topic) params.set("topic", filter.topic);
      if (filter.area) params.set("area", filter.area);
      if (filter.severity) params.set("severity", filter.severity);
      const json = await apiFetch<{ data?: FeedRow[] }>(`/api/feedback/recent?${params}`);
      return json.data ?? [];
    },
    enabled: open,
    staleTime: 30_000,
  });

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full max-w-md overflow-y-auto">
        <SheetHeader className="flex flex-row items-start justify-between pb-4 border-b">
          <SheetTitle className="text-base font-display leading-tight pr-6">{filter?.title ?? "Chi tiết"}</SheetTitle>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors mt-0.5">
            <X className="h-4 w-4" />
          </button>
        </SheetHeader>
        <div className="pt-4 space-y-3">
          {isLoading ? (
            <p className="text-sm text-muted-foreground text-center py-8">Đang tải...</p>
          ) : !data || data.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">Không có phản hồi phù hợp</p>
          ) : (
            data.map((f) => (
              <div key={f.id} className="rounded-xl border border-border bg-card p-3 space-y-1.5">
                <p className="text-sm">{f.text}</p>
                <div className="flex flex-wrap gap-1.5">
                  {f.topic && <Pill tone="mint">{f.topic}</Pill>}
                  {f.sentiment && <Pill tone={f.sentiment === "negative" ? "coral" : "green"}>{f.sentiment}</Pill>}
                  {f.severity && <Pill tone="deep">{f.severity}</Pill>}
                  {f.area && (
                    <span className="text-[10px] font-mono text-muted-foreground inline-flex items-center gap-1">
                      <MapPin className="h-3 w-3" />{f.area}
                    </span>
                  )}
                </div>
                <div className="text-[10px] font-mono text-muted-foreground">
                  {new Date(f.created_at).toLocaleString("vi-VN")}
                </div>
              </div>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
