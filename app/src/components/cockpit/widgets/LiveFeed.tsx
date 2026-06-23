import { useRef, useState, useEffect } from "react";
import { MapPin, Radio } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { Database as DatabaseSchema } from "@/integrations/supabase/types";
import { apiFetch } from "@/lib/api";
import { Card, Pill, SectionHeader } from "../primitives";

type FeedRow = DatabaseSchema["public"]["Tables"]["feedback"]["Row"];

export function LiveFeed() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["feedback-recent"],
    queryFn: async () => {
      const json = await apiFetch<{ data?: FeedRow[] }>("/api/feedback/recent?limit=8");
      return json.data ?? [];
    },
    staleTime: 15_000,
    refetchInterval: false, // Realtime invalidates via useCockpitRealtime
  });

  const feed = data ?? [];
  const streamStatus = isError ? "error" : isLoading ? "connecting" : "live";

  // Highlight row mới khi data thay đổi.
  const prevIdsRef = useRef<Set<string>>(new Set());
  const [newFeedIds, setNewFeedIds] = useState<Set<string>>(new Set());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!data) return;
    const freshIds = data.map((r) => r.id).filter((id) => !prevIdsRef.current.has(id));
    data.forEach((r) => prevIdsRef.current.add(r.id));
    if (freshIds.length > 0 && prevIdsRef.current.size > freshIds.length) {
      setNewFeedIds(new Set(freshIds));
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setNewFeedIds(new Set()), 1600);
    }
  }, [data]);

  return (
    <Card>
      <SectionHeader
        icon={Radio}
        title="Live feedback stream"
        subtitle="Multi-channel · app, rating, hotline, CS, survey"
        right={
          <span className={`text-[11px] font-mono inline-flex items-center gap-1.5 ${streamStatus === "error" ? "text-xanh-coral" : "text-xanh-green"}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
            {streamStatus === "live" ? "streaming" : streamStatus === "error" ? "disconnected" : "connecting"}
          </span>
        }
      />
      <div className="divide-y divide-border">
        {isLoading ? (
          <div className="px-5 py-12 flex flex-col items-center justify-center text-center text-muted-foreground">
            <Radio className="h-8 w-8 animate-pulse text-xanh-green mb-3" />
            <p className="font-semibold text-foreground">Đang tải phản hồi...</p>
            <p className="text-sm mt-1">Kết nối với hệ thống Supabase...</p>
          </div>
        ) : feed.length === 0 ? (
          <div className="px-5 py-12 flex flex-col items-center justify-center text-center text-muted-foreground">
            <Radio className="h-8 w-8 text-muted-foreground/50 mb-3" />
            <p className="font-semibold text-foreground">Chưa có luồng dữ liệu</p>
            <p className="text-sm mt-1 max-w-sm">Chưa có phản hồi. Thêm dữ liệu tại trang Phản hồi để xem luồng trực tiếp.</p>
          </div>
        ) : (
          feed.map((f) => (
            <div
              key={f.id}
              className={`px-5 py-3 grid grid-cols-12 gap-3 items-center hover:bg-xanh-mint/30 transition-colors ${newFeedIds.has(f.id) ? "live-feedback-row-new" : ""}`}
            >
              <span className="col-span-2 sm:col-span-1 text-[10px] font-mono uppercase text-muted-foreground">{f.channel}</span>
              <p className="col-span-10 sm:col-span-7 text-sm">{f.text}</p>
              <div className="col-span-12 sm:col-span-4 flex flex-wrap justify-start sm:justify-end gap-1.5">
                {f.topic && <Pill tone="mint">{f.topic}</Pill>}
                {f.sentiment && <Pill tone={f.sentiment === "negative" ? "coral" : "green"}>{f.sentiment}</Pill>}
                {f.severity && <Pill tone="deep">{f.severity}</Pill>}
                {f.area && (
                  <span className="text-[10px] font-mono text-muted-foreground inline-flex items-center gap-1">
                    <MapPin className="h-3 w-3" />{f.area}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
