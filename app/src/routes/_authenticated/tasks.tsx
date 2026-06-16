import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Loader2, Kanban, ChevronDown, ChevronUp, MapPin, Tag, ShieldAlert, CheckCircle2, Clock } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/lib/api";
import { regionLabel } from "@/lib/regions";

export const Route = createFileRoute("/_authenticated/tasks")({
  component: TasksPage,
});

type Task = {
  id: string;
  title: string;
  summary: string | null;
  assigned_team: string;
  topic: string | null;
  area: string | null;
  priority: string;
  status: string;
  created_at: string;
};

type Alert = {
  id: string;
  title: string;
  severity: string;
  status: string;
  task_id: string;
  created_at: string;
};

const API_BASE = import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000";

function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [alerts, setAlerts] = useState<Record<string, Alert[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const { data: me } = useMe();
  const isManager = me?.role === "admin" || me?.role === "manager" || me?.role === "staff";

  async function loadData() {
    if (!isManager) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/tasks?limit=50`);
      if (!res.ok) throw new Error("Failed to fetch tasks");
      const json = await res.json();
      setTasks(json.data || []);
    } catch (err) {
      toast.error("Không thể tải danh sách Task.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (me?.role && isManager) loadData();
  }, [me?.role]);

  async function toggleTask(taskId: string) {
    if (expandedTask === taskId) {
      setExpandedTask(null);
      return;
    }
    setExpandedTask(taskId);
    if (!alerts[taskId]) {
      try {
        const { data, error } = await supabase.from("alerts").select("*").eq("task_id", taskId).order("created_at", { ascending: false });
        if (error) throw error;
        setAlerts((prev) => ({ ...prev, [taskId]: data as Alert[] }));
      } catch (err) {
        toast.error("Không thể tải chi tiết ticket.");
      }
    }
  }

  async function updateTaskStatus(taskId: string, newStatus: string) {
    try {
      const { error } = await supabase.from("tasks").update({ status: newStatus }).eq("id", taskId);
      if (error) throw error;
      toast.success(`Đã chuyển trạng thái thành ${newStatus}`);
      setTasks(tasks.map(t => t.id === taskId ? { ...t, status: newStatus } : t));
    } catch (err) {
      toast.error("Lỗi cập nhật trạng thái.");
    }
  }

  if (!isManager) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Bạn không có quyền xem trang này.
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
      <div>
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Kanban className="h-8 w-8 text-xanh-deep" />
          Task Manager
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hệ thống tự động gom nhóm các ticket (alerts) trùng lặp thành Task chung để dễ quản lý và xử lý dứt điểm.
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="text-center p-12 border border-border rounded-2xl bg-white text-muted-foreground shadow-sm">
          Chưa có Task nào được tự động tạo.
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => {
            const isExpanded = expandedTask === task.id;
            const childAlerts = alerts[task.id] || [];
            
            return (
              <div key={task.id} className="rounded-2xl border border-border bg-white shadow-[var(--shadow-card)] overflow-hidden transition-all hover:border-xanh-green/30">
                {/* Header / Summary */}
                <div 
                  onClick={() => toggleTask(task.id)}
                  className="p-5 cursor-pointer flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center hover:bg-muted/10 transition-colors"
                >
                  <div className="flex-1 space-y-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase
                        ${task.status === "open" ? "bg-amber-100 text-amber-800" : task.status === "in_progress" ? "bg-blue-100 text-blue-800" : "bg-green-100 text-green-800"}`}
                      >
                        {task.status}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                        Team: {task.assigned_team}
                      </span>
                      {task.area && (
                        <span className="text-[11px] text-muted-foreground font-mono flex items-center gap-1">
                          <MapPin className="h-3 w-3" /> {regionLabel(task.area)}
                        </span>
                      )}
                    </div>
                    <h3 className="font-semibold text-lg text-xanh-deep leading-tight">{task.title}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">{task.summary}</p>
                  </div>
                  
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-4 w-4" />
                      <span className="font-mono text-xs">{new Date(task.created_at).toLocaleDateString("vi-VN")}</span>
                    </div>
                    {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </div>
                </div>

                {/* Expanded Body */}
                {isExpanded && (
                  <div className="border-t border-border bg-muted/10 p-5 space-y-5 animate-in slide-in-from-top-2">
                    <div className="flex flex-wrap gap-2">
                      <button 
                        onClick={(e) => { e.stopPropagation(); updateTaskStatus(task.id, "in_progress"); }}
                        disabled={task.status === "in_progress"}
                        className="px-4 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        Tiếp nhận (In Progress)
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); updateTaskStatus(task.id, "resolved"); }}
                        disabled={task.status === "resolved"}
                        className="px-4 py-2 bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1"
                      >
                        <CheckCircle2 className="h-4 w-4" /> Hoàn thành (Resolved)
                      </button>
                    </div>

                    <div>
                      <h4 className="font-semibold text-sm flex items-center gap-2 mb-3">
                        <ShieldAlert className="h-4 w-4 text-amber-600" />
                        Danh sách Ticket liên quan ({childAlerts.length})
                      </h4>
                      {childAlerts.length === 0 ? (
                        <div className="text-xs text-muted-foreground p-4 bg-white rounded-lg border border-border">
                          Đang tải hoặc không có ticket...
                        </div>
                      ) : (
                        <div className="bg-white border border-border rounded-xl overflow-hidden divide-y divide-border">
                          {childAlerts.map(alert => (
                            <div key={alert.id} className="p-3 text-sm flex justify-between items-center hover:bg-muted/30">
                              <div className="space-y-1">
                                <p className="font-medium text-xanh-deep">{alert.title}</p>
                                <p className="text-[11px] font-mono text-muted-foreground flex items-center gap-2">
                                  <span>{new Date(alert.created_at).toLocaleString("vi-VN")}</span>
                                  <span>•</span>
                                  <span className={`px-1.5 py-0.5 rounded text-white ${alert.severity === "P5" ? "bg-red-600" : "bg-amber-500"}`}>
                                    {alert.severity}
                                  </span>
                                </p>
                              </div>
                              <span className="text-[10px] uppercase font-mono px-2 py-1 bg-muted rounded">
                                {alert.status}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
