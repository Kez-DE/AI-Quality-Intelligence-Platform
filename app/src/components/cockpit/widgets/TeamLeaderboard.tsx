import { useQuery } from "@tanstack/react-query";
import { Target } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Card, SectionHeader } from "../primitives";

export function TeamLeaderboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["leaderboard"],
    queryFn: async () => {
      const json = await apiFetch<{ data: any[] }>("/api/leaderboard");
      return (json.data ?? []).slice(0, 5);
    },
    staleTime: 60_000,
    retry: false,
  });

  return (
    <Card>
      <SectionHeader icon={Target} title="Team Leaderboard" subtitle="Top resolution speed & tasks done" />
      <div className="px-3 pb-3 space-y-2">
        {isLoading ? (
          <div className="p-4 text-center text-xs text-muted-foreground">Loading...</div>
        ) : !data || data.length === 0 ? (
          <div className="p-4 text-center text-xs text-muted-foreground">Chưa có dữ liệu.</div>
        ) : (
          data.map((t, idx) => (
            <div key={t.team} className="flex items-center justify-between rounded-xl border border-border bg-card p-3">
              <div className="flex items-center gap-3">
                <span className={`font-bold text-sm ${idx === 0 ? "text-yellow-600" : idx === 1 ? "text-gray-400" : idx === 2 ? "text-orange-600" : "text-muted-foreground"}`}>
                  #{idx + 1}
                </span>
                <div>
                  <div className="font-mono text-sm font-semibold text-xanh-deep">{t.team}</div>
                  <div className="text-[11px] text-muted-foreground">{t.resolved_count} ticket</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold text-xanh-green">{t.avg_resolution_hours}h</div>
                <div className="text-[11px] text-muted-foreground font-mono">avg time</div>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
