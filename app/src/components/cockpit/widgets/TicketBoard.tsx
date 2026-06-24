import { useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Card, Pill, SectionHeader } from "../primitives";

interface Task {
  id: string;
  title: string;
  priority: string;
  status: string;
  assigned_team: string;
  due_at: string | null;
}

const STATUS_COLS = [
  { key: "open", label: "Triage", color: "var(--xanh-deep)" },
  { key: "in_progress", label: "In progress", color: "var(--xanh-green)" },
  { key: "resolved", label: "Resolved", color: "var(--xanh-cyan)" },
];

function sevTone(p: string): "coral" | "amber" | "mint" {
  if (p === "P5" || p === "P0") return "coral";
  if (p === "P4" || p === "P3" || p === "P1") return "amber";
  return "mint";
}

export function TicketBoard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiFetch<{ data?: Task[] }>("/api/tasks?limit=30")
      .then((json) => { if (active) setTasks(json.data ?? []); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const byStatus = (key: string) => tasks.filter((t) => t.status === key).slice(0, 4);

  return (
    <Card>
      <SectionHeader
        icon={ClipboardList}
        title="Ticket board · SLA tracking"
        subtitle="Từ alert → ticket → xử lý → correction log feedback loop"
      />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4">
        {loading ? (
          <div className="col-span-3 py-8 text-center text-xs text-muted-foreground">Loading...</div>
        ) : (
          STATUS_COLS.map((col) => {
            const items = byStatus(col.key);
            return (
              <div key={col.key} className="rounded-xl border border-border bg-gradient-to-b from-card to-muted/40 p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: col.color }}>{col.label}</span>
                  <span className="text-[10px] font-mono text-muted-foreground">{items.length}</span>
                </div>
                <div className="space-y-2">
                  {items.length === 0 ? (
                    <p className="text-[11px] text-muted-foreground text-center py-3">Trống</p>
                  ) : (
                    items.map((t) => (
                      <div key={t.id} className="rounded-lg border border-border bg-card p-2.5 hover:shadow-sm transition-shadow">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[10px] text-muted-foreground">{t.assigned_team}</span>
                          <Pill tone={sevTone(t.priority)}>{t.priority}</Pill>
                        </div>
                        <p className="text-sm mt-1 leading-snug line-clamp-2">{t.title}</p>
                        {t.due_at && (
                          <div className="text-[10px] font-mono text-muted-foreground mt-1">
                            due {new Date(t.due_at).toLocaleDateString("vi-VN", { month: "numeric", day: "numeric" })}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
