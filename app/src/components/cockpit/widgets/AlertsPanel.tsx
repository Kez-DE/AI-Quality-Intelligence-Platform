import { useEffect, useState } from "react";
import { Bell, CheckCircle2, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Card, Pill, SectionHeader } from "../primitives";

interface Alert {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  created_at: string;
  assigned_team?: string | null;
  priority?: string | null;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins}′`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

function sevTone(sev: string): "coral" | "amber" | "mint" {
  if (sev === "P5" || sev === "P4" || sev === "P0") return "coral";
  if (sev === "P3" || sev === "P1") return "amber";
  return "mint";
}

function AlertsSkeleton() {
  return (
    <div className="px-3 pb-3 space-y-2">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-3 animate-pulse">
          <div className="flex items-start gap-2">
            <div className="h-5 w-8 bg-muted rounded" />
            <div className="flex-1 space-y-1.5">
              <div className="h-3.5 bg-muted rounded w-3/4" />
              <div className="h-2.5 bg-muted rounded w-1/3" />
            </div>
            <div className="h-3 w-6 bg-muted rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function AlertsPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);
    apiFetch<{ data?: Alert[] }>("/api/alerts/recent?limit=5")
      .then((json) => {
        if (active) setAlerts((json.data ?? []).filter((a) => a.status === "open").slice(0, 5));
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [retryCount]);

  return (
    <Card>
      <SectionHeader icon={Bell} title="Alerts đang mở" subtitle="Anomaly detection · spike & pattern" />
      {loading ? (
        <AlertsSkeleton />
      ) : error ? (
        <div className="px-3 py-6 text-center text-sm text-muted-foreground">
          Không tải được.{" "}
          <button
            onClick={() => setRetryCount((c) => c + 1)}
            className="text-xanh-green hover:underline underline-offset-2 inline-flex items-center gap-1"
          >
            <RefreshCw className="h-3 w-3" /> Thử lại
          </button>
        </div>
      ) : alerts.length === 0 ? (
        <div className="px-3 py-6 flex flex-col items-center text-center gap-2">
          <div className="h-10 w-10 rounded-full bg-xanh-mint/60 grid place-items-center">
            <CheckCircle2 className="h-5 w-5 text-xanh-green" />
          </div>
          <p className="text-sm font-semibold text-foreground">Tình trạng tốt</p>
          <p className="text-xs text-muted-foreground max-w-[200px]">
            Không có alert đang mở — hệ thống hoạt động bình thường.
          </p>
        </div>
      ) : (
        <div className="px-3 pb-3 space-y-2">
          {alerts.map((a) => {
            const sev = a.severity ?? a.priority ?? "P2";
            return (
              <div key={a.id} className="rounded-xl border border-border bg-card p-3 hover:border-xanh-green/50 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2">
                    <Pill tone={sevTone(sev)}>{sev}</Pill>
                    <div>
                      <div className="text-sm font-semibold leading-tight">{a.title}</div>
                      {a.assigned_team && (
                        <div className="text-[11px] text-muted-foreground mt-0.5">{a.assigned_team}</div>
                      )}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-muted-foreground whitespace-nowrap">{timeAgo(a.created_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
