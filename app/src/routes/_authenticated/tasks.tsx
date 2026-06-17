import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useCallback } from "react";
import {
  Loader2,
  Kanban,
  ChevronDown,
  ChevronUp,
  MapPin,
  ShieldAlert,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Filter,
  UserPlus,
  CalendarClock,
} from "lucide-react";
import { toast } from "sonner";
import { useMe, apiFetch } from "@/lib/api";
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
  owner_id: string | null;
  owner_email: string | null;
  due_at: string | null;
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

type AssignableUser = {
  id: string;
  email: string;
  role: string;
  full_name: string | null;
};

type AssignableUsersResponse = {
  data: AssignableUser[];
};

const TEAMS = ["All", "Safety", "CSKH", "IT", "Vận hành", "Pricing", "Marketing"] as const;
const STATUSES = ["All", "open", "in_progress", "resolved"] as const;
const PRIORITIES = ["All", "P1", "P2", "P3", "P4", "P5"] as const;

const STATUS_LABELS: Record<string, string> = {
  All: "All",
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
};

function isOverdue(task: Task): boolean {
  if (!task.due_at) return false;
  if (task.status === "resolved") return false;
  return new Date(task.due_at) < new Date();
}

function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [alerts, setAlerts] = useState<Record<string, Alert[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [assignableUsers, setAssignableUsers] = useState<AssignableUser[]>([]);
  const [assigningTask, setAssigningTask] = useState<string | null>(null);

  // Filter state
  const [filterStatus, setFilterStatus] = useState<string>("All");
  const [filterTeam, setFilterTeam] = useState<string>("All");
  const [filterPriority, setFilterPriority] = useState<string>("All");
  const [filterOverdue, setFilterOverdue] = useState(false);

  // Assignment form state per task
  const [assignForm, setAssignForm] = useState<Record<string, { owner_id: string; due_at: string }>>({});

  const { data: me } = useMe();
  const isManager = me?.role === "admin" || me?.role === "manager" || me?.role === "staff";

  const buildQueryString = useCallback(() => {
    const params = new URLSearchParams();
    params.set("limit", "50");
    if (filterStatus !== "All") params.set("status", filterStatus);
    if (filterTeam !== "All") params.set("team", filterTeam);
    if (filterPriority !== "All") params.set("priority", filterPriority);
    if (filterOverdue) params.set("overdue", "true");
    return params.toString();
  }, [filterStatus, filterTeam, filterPriority, filterOverdue]);

  async function loadData() {
    if (!isManager) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const qs = buildQueryString();
      const json = await apiFetch<{ data: Task[] }>(`/api/tasks?${qs}`);
      setTasks(json.data || []);
    } catch {
      toast.error("Không thể tải danh sách Task.");
    } finally {
      setLoading(false);
    }
  }

  async function loadAssignableUsers() {
    try {
      const json = await apiFetch<AssignableUsersResponse>("/api/users/assignable");
      setAssignableUsers(json.data || []);
    } catch {
      // Silently fail - users list is non-critical
    }
  }

  useEffect(() => {
    if (me?.role && isManager) {
      loadData();
      loadAssignableUsers();
    }
  }, [me?.role]);

  useEffect(() => {
    if (me?.role && isManager) {
      loadData();
    }
  }, [filterStatus, filterTeam, filterPriority, filterOverdue]);

  async function toggleTask(taskId: string) {
    if (expandedTask === taskId) {
      setExpandedTask(null);
      return;
    }
    setExpandedTask(taskId);
    if (!alerts[taskId]) {
      try {
        const json = await apiFetch<{ data: Alert[] }>(`/api/tasks/${taskId}/alerts`);
        setAlerts((prev) => ({ ...prev, [taskId]: (json.data || []) as Alert[] }));
      } catch {
        toast.error("Không thể tải chi tiết ticket.");
      }
    }
  }

  async function updateTaskStatus(taskId: string, newStatus: string) {
    try {
      await apiFetch(`/api/tasks/${taskId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      toast.success(`Đã chuyển trạng thái thành ${newStatus}`);
      setTasks(tasks.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t)));
    } catch {
      toast.error("Lỗi cập nhật trạng thái.");
    }
  }

  async function assignTask(taskId: string) {
    const form = assignForm[taskId];
    if (!form || !form.owner_id) {
      toast.error("Vui lòng chọn người nhận.");
      return;
    }
    setAssigningTask(taskId);
    try {
      await apiFetch(`/api/tasks/${taskId}/assign`, {
        method: "PATCH",
        body: JSON.stringify({
          owner_id: form.owner_id,
          due_at: form.due_at || null,
        }),
      });
      const assignedUser = assignableUsers.find((u) => u.id === form.owner_id);
      setTasks(
        tasks.map((t) =>
          t.id === taskId
            ? { ...t, owner_id: form.owner_id, owner_email: assignedUser?.email || null, due_at: form.due_at || null }
            : t
        )
      );
      toast.success("Đã gán task thành công.");
    } catch {
      toast.error("Lỗi khi gán task.");
    } finally {
      setAssigningTask(null);
    }
  }

  function updateAssignForm(taskId: string, field: "owner_id" | "due_at", value: string) {
    setAssignForm((prev) => ({
      ...prev,
      [taskId]: {
        owner_id: prev[taskId]?.owner_id || "",
        due_at: prev[taskId]?.due_at || "",
        [field]: value,
      },
    }));
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

      {/* Filter Bar */}
      <div className="rounded-2xl border border-border bg-white shadow-[var(--shadow-card)] p-4">
        <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-xanh-deep">
          <Filter className="h-4 w-4" />
          Bộ lọc
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-muted-foreground">Status:</span>
            <div className="flex rounded-lg border border-border overflow-hidden">
              {STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => setFilterStatus(s)}
                  className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
                    filterStatus === s
                      ? "bg-xanh-deep text-white"
                      : "bg-white text-muted-foreground hover:bg-muted/30"
                  }`}
                >
                  {STATUS_LABELS[s]}
                </button>
              ))}
            </div>
          </div>

          {/* Team Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-muted-foreground">Team:</span>
            <select
              value={filterTeam}
              onChange={(e) => setFilterTeam(e.target.value)}
              className="px-3 py-1.5 text-xs font-semibold border border-border rounded-lg bg-white text-xanh-deep focus:outline-none focus:ring-2 focus:ring-xanh-green/30"
            >
              {TEAMS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Priority Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-muted-foreground">Priority:</span>
            <div className="flex rounded-lg border border-border overflow-hidden">
              {PRIORITIES.map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterPriority(p)}
                  className={`px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                    filterPriority === p
                      ? "bg-xanh-deep text-white"
                      : "bg-white text-muted-foreground hover:bg-muted/30"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Overdue Toggle */}
          <button
            onClick={() => setFilterOverdue(!filterOverdue)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
              filterOverdue
                ? "bg-red-100 text-red-700 border-red-300"
                : "bg-white text-muted-foreground border-border hover:bg-muted/30"
            }`}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Quá hạn
          </button>
        </div>
      </div>

      {/* Task List */}
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
            const overdue = isOverdue(task);

            return (
              <div
                key={task.id}
                className="rounded-2xl border border-border bg-white shadow-[var(--shadow-card)] overflow-hidden transition-all hover:border-xanh-green/30"
              >
                {/* Header / Summary */}
                <div
                  onClick={() => toggleTask(task.id)}
                  className="p-5 cursor-pointer flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center hover:bg-muted/10 transition-colors"
                >
                  <div className="flex-1 space-y-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                          task.status === "open"
                            ? "bg-amber-100 text-amber-800"
                            : task.status === "in_progress"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-green-100 text-green-800"
                        }`}
                      >
                        {task.status}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                        Team: {task.assigned_team}
                      </span>
                      {task.priority && (
                        <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                          {task.priority}
                        </span>
                      )}
                      {overdue && (
                        <span className="bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded">
                          QUA HAN
                        </span>
                      )}
                      {task.area && (
                        <span className="text-[11px] text-muted-foreground font-mono flex items-center gap-1">
                          <MapPin className="h-3 w-3" /> {regionLabel(task.area)}
                        </span>
                      )}
                    </div>
                    <h3 className="font-semibold text-lg text-xanh-deep leading-tight">{task.title}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">{task.summary}</p>
                    {task.owner_email && (
                      <p className="text-[11px] font-mono text-xanh-green flex items-center gap-1">
                        <UserPlus className="h-3 w-3" /> {task.owner_email}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    {task.due_at && (
                      <div className={`flex items-center gap-1.5 ${overdue ? "text-red-600" : ""}`}>
                        <CalendarClock className="h-4 w-4" />
                        <span className="font-mono text-xs">
                          {new Date(task.due_at).toLocaleDateString("vi-VN")}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-4 w-4" />
                      <span className="font-mono text-xs">
                        {new Date(task.created_at).toLocaleDateString("vi-VN")}
                      </span>
                    </div>
                    {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </div>
                </div>

                {/* Expanded Body */}
                {isExpanded && (
                  <div className="border-t border-border bg-muted/10 p-5 space-y-5 animate-in slide-in-from-top-2">
                    {/* Status buttons */}
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          updateTaskStatus(task.id, "in_progress");
                        }}
                        disabled={task.status === "in_progress"}
                        className="px-4 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        Tiep nhan (In Progress)
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          updateTaskStatus(task.id, "resolved");
                        }}
                        disabled={task.status === "resolved"}
                        className="px-4 py-2 bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1"
                      >
                        <CheckCircle2 className="h-4 w-4" /> Hoan thanh (Resolved)
                      </button>
                    </div>

                    {/* Assignment Section */}
                    <div className="rounded-xl border border-border bg-white p-4 space-y-3">
                      <h4 className="font-semibold text-sm flex items-center gap-2 text-xanh-deep">
                        <UserPlus className="h-4 w-4" />
                        Gan task
                      </h4>
                      {task.owner_email && (
                        <p className="text-xs text-muted-foreground font-mono">
                          Hien tai: <span className="text-xanh-green font-semibold">{task.owner_email}</span>
                        </p>
                      )}
                      <div className="flex flex-wrap items-end gap-3">
                        <div className="space-y-1">
                          <label className="text-[11px] font-mono text-muted-foreground">Nguoi nhan</label>
                          <select
                            value={assignForm[task.id]?.owner_id || task.owner_id || ""}
                            onChange={(e) => updateAssignForm(task.id, "owner_id", e.target.value)}
                            className="px-3 py-2 text-xs border border-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-xanh-green/30 min-w-[200px]"
                          >
                            <option value="">-- Chon nguoi --</option>
                            {assignableUsers.map((user) => (
                              <option key={user.id} value={user.id}>
                                {user.full_name || user.email} ({user.role})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1">
                          <label className="text-[11px] font-mono text-muted-foreground">Han hoan thanh</label>
                          <input
                            type="date"
                            value={assignForm[task.id]?.due_at || (task.due_at ? task.due_at.split("T")[0] : "")}
                            onChange={(e) => updateAssignForm(task.id, "due_at", e.target.value)}
                            className="px-3 py-2 text-xs border border-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-xanh-green/30"
                          />
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            assignTask(task.id);
                          }}
                          disabled={assigningTask === task.id}
                          className="px-4 py-2 bg-xanh-deep text-white hover:bg-xanh-deep/90 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1"
                        >
                          {assigningTask === task.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <UserPlus className="h-3.5 w-3.5" />
                          )}
                          Gan
                        </button>
                      </div>
                    </div>

                    {/* Child Alerts */}
                    <div>
                      <h4 className="font-semibold text-sm flex items-center gap-2 mb-3">
                        <ShieldAlert className="h-4 w-4 text-amber-600" />
                        Danh sach Ticket lien quan ({childAlerts.length})
                      </h4>
                      {childAlerts.length === 0 ? (
                        <div className="text-xs text-muted-foreground p-4 bg-white rounded-lg border border-border">
                          Dang tai hoac khong co ticket...
                        </div>
                      ) : (
                        <div className="bg-white border border-border rounded-xl overflow-hidden divide-y divide-border">
                          {childAlerts.map((alert) => (
                            <div
                              key={alert.id}
                              className="p-3 text-sm flex justify-between items-center hover:bg-muted/30"
                            >
                              <div className="space-y-1">
                                <p className="font-medium text-xanh-deep">{alert.title}</p>
                                <p className="text-[11px] font-mono text-muted-foreground flex items-center gap-2">
                                  <span>{new Date(alert.created_at).toLocaleString("vi-VN")}</span>
                                  <span>&bull;</span>
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-white ${
                                      alert.severity === "P5" ? "bg-red-600" : "bg-amber-500"
                                    }`}
                                  >
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
