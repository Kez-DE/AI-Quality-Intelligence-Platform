import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
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

export function AlertsPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiFetch<{ data?: Alert[] }>("/api/alerts/recent?limit=5")
      .then((json) => { if (active) setAlerts((json.data ?? []).filter((a) => a.status === "open").slice(0, 5)); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <Card>
      <SectionHeader icon={Bell} title="Alerts đang mở" subtitle="Anomaly detection · spike & pattern" />
      <div className="px-3 pb-3 space-y-2">
        {loading ? (
          <div className="py-6 text-center text-xs text-muted-foreground">Loading...</div>
        ) : alerts.length === 0 ? (
          <div className="py-6 text-center text-xs text-muted-foreground">Không có alert đang mở</div>
        ) : (
          alerts.map((a) => {
            const sev = a.severity ?? a.priority ?? "P2";
            return (
              <div key={a.id} className="rounded-xl border border-border bg-white p-3 hover:border-xanh-green/50 transition-colors">
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
          })
        )}
      </div>
    </Card>
  );
}
