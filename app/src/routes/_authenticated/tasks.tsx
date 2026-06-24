import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useCallback, useMemo } from "react";
import {
  Loader2,
  Kanban,
  Building2,
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
  ClipboardCheck,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { ALL_TEAMS, useMe, apiFetch, isUnassignedOps } from "@/lib/api";
import { NoDepartmentNotice } from "@/components/NoDepartmentNotice";
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
  report_id?: string | null;
  source?: string;
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
  department: string | null;
};

type AssignableUsersResponse = {
  data: AssignableUser[];
};

const TEAMS = ["All", ...ALL_TEAMS] as const;
const STATUSES = ["All", "open", "in_progress", "resolved"] as const;
const PRIORITIES = ["All", "P1", "P2", "P3", "P4", "P5"] as const;

const STATUS_LABELS: Record<string, string> = {
  All: "Tất cả",
  open: "Đang mở",
  in_progress: "Đang xử lý",
  resolved: "Đã xong",
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
  const [filterMine, setFilterMine] = useState(false);

  // Assignment form state per task
  const [assignForm, setAssignForm] = useState<
    Record<string, { owner_id: string; due_at: string }>
  >({});

  // Completion-report form state per task (staff -> manager)
  const [reportForm, setReportForm] = useState<
    Record<string, { note: string; level: string }>
  >({});
  const [submittingReport, setSubmittingReport] = useState<string | null>(null);

  // Gợi ý người nhận (agent rule-based) per task
  const [suggestion, setSuggestion] = useState<
    Record<string, { id: string; email: string; full_name: string | null; open_tasks: number; reason: string }>
  >({});
  const [loadingSuggestion, setLoadingSuggestion] = useState<string | null>(null);

  const { data: me } = useMe();
  const isOps = me?.role === "admin" || me?.role === "manager" || me?.role === "staff";
  const isAdmin = me?.role === "admin";

  // Phân bổ task theo phòng ban (cho admin xem toàn cảnh ticket được đẩy đi đâu).
  const deptCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const t of tasks) {
      const team = t.assigned_team || "—";
      counts[team] = (counts[team] || 0) + 1;
    }
    return counts;
  }, [tasks]);

  const buildQueryString = useCallback(() => {
    const params = new URLSearchParams();
    params.set("limit", "50");
    if (filterStatus !== "All") params.set("status", filterStatus);
    if (filterTeam !== "All") params.set("team", filterTeam);
    if (filterPriority !== "All") params.set("priority", filterPriority);
    if (filterOverdue) params.set("overdue", "true");
    if (filterMine) params.set("mine", "true");
    return params.toString();
  }, [filterStatus, filterTeam, filterPriority, filterOverdue, filterMine]);

  async function loadData() {
    if (!isOps) {
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
    if (me?.role && isOps) {
      loadData();
      loadAssignableUsers();
    }
  }, [me?.role]);

  useEffect(() => {
    if (me?.role && isOps) {
      loadData();
    }
  }, [filterStatus, filterTeam, filterPriority, filterOverdue, filterMine]);

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
            ? {
                ...t,
                owner_id: form.owner_id,
                owner_email: assignedUser?.email || null,
                due_at: form.due_at || null,
              }
            : t,
        ),
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

  function updateReportForm(taskId: string, field: "note" | "level", value: string) {
    setReportForm((prev) => ({
      ...prev,
      [taskId]: {
        note: prev[taskId]?.note || "",
        level: prev[taskId]?.level || "completed",
        [field]: value,
      },
    }));
  }

  async function loadSuggestion(taskId: string) {
    setLoadingSuggestion(taskId);
    try {
      const json = await apiFetch<{
        data: { suggested: { id: string; email: string; full_name: string | null; open_tasks: number } | null; reason: string };
      }>(`/api/tasks/${taskId}/suggest-assignee`);
      const s = json.data?.suggested;
      if (!s) {
        toast.info(json.data?.reason || "Chưa có người phù hợp để gợi ý.");
        return;
      }
      setSuggestion((prev) => ({
        ...prev,
        [taskId]: { ...s, reason: json.data.reason },
      }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Lỗi khi lấy gợi ý.");
    } finally {
      setLoadingSuggestion(null);
    }
  }

  async function submitCompletionReport(taskId: string) {
    const form = reportForm[taskId];
    if (!form || !form.note.trim()) {
      toast.error("Vui lòng nhập nội dung báo cáo.");
      return;
    }
    setSubmittingReport(taskId);
    try {
      await apiFetch(`/api/tasks/${taskId}/completion-report`, {
        method: "POST",
        body: JSON.stringify({
          note: form.note.trim(),
          completion_level: form.level || "completed",
        }),
      });
      toast.success("Đã gửi báo cáo hoàn thành cho quản lý.");
      setReportForm((prev) => ({ ...prev, [taskId]: { note: "", level: "completed" } }));
      // Nếu báo "completed", backend chuyển task -> resolved; cập nhật UI.
      if ((form.level || "completed") === "completed") {
        setTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, status: "resolved" } : t)),
        );
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Lỗi khi gửi báo cáo.");
    } finally {
      setSubmittingReport(null);
    }
  }

  if (!isOps) {
    return (
      <div className="p-8 text-center text-muted-foreground">Bạn không có quyền xem trang này.</div>
    );
  }

  if (isUnassignedOps(me)) {
    return (
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Kanban className="h-8 w-8 text-xanh-deep" />
          Quản lý công việc
        </h1>
        <NoDepartmentNotice />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
      <div>
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Kanban className="h-8 w-8 text-xanh-deep" />
          Quản lý công việc
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hệ thống tự động gom nhóm các ticket (alerts) trùng lặp thành Task chung để dễ quản lý và
          xử lý dứt điểm.
        </p>
      </div>

      {/* Admin: phân bổ ticket/task theo phòng ban — bấm để lọc nhanh */}
      {isAdmin && (
        <div className="rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] p-4">
          <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-xanh-deep">
            <Building2 className="h-4 w-4" />
            Phân bổ task theo phòng ban
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {ALL_TEAMS.map((team) => {
              const active = filterTeam === team;
              return (
                <button
                  key={team}
                  onClick={() => setFilterTeam(active ? "All" : team)}
                  className={`rounded-xl border p-3 text-left transition-colors ${
                    active
                      ? "border-xanh-green/50 bg-xanh-green/10"
                      : "border-border bg-muted/10 hover:bg-muted/30"
                  }`}
                >
                  <div className="text-[11px] font-mono text-muted-foreground truncate">{team}</div>
                  <div className="text-2xl font-bold text-xanh-deep">{deptCounts[team] || 0}</div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] p-4">
        <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-xanh-deep">
          <Filter className="h-4 w-4" />
          Bộ lọc
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-muted-foreground">Trạng thái:</span>
            <div className="flex rounded-lg border border-border overflow-hidden">
              {STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => setFilterStatus(s)}
                  className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
                    filterStatus === s
                      ? "bg-xanh-deep text-white"
                      : "bg-card text-muted-foreground hover:bg-muted/30"
                  }`}
                >
                  {STATUS_LABELS[s]}
                </button>
              ))}
            </div>
          </div>

          {/* Team Filter — chỉ admin chọn được phòng; ops khác bị backend ép về phòng mình */}
          {isAdmin ? (
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-mono text-muted-foreground">Phòng ban:</span>
              <select
                value={filterTeam}
                onChange={(e) => setFilterTeam(e.target.value)}
                className="px-3 py-1.5 text-xs font-semibold border border-border rounded-lg bg-card text-xanh-deep focus:outline-none focus:ring-2 focus:ring-xanh-green/30"
              >
                {TEAMS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            me?.department && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-mono text-muted-foreground">Phòng ban:</span>
                <span className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-muted/40 text-xanh-deep">
                  {me.department}
                </span>
              </div>
            )
          )}

          {/* Priority Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-muted-foreground">Mức độ:</span>
            <div className="flex rounded-lg border border-border overflow-hidden">
              {PRIORITIES.map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterPriority(p)}
                  className={`px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                    filterPriority === p
                      ? "bg-xanh-deep text-white"
                      : "bg-card text-muted-foreground hover:bg-muted/30"
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
                : "bg-card text-muted-foreground border-border hover:bg-muted/30"
            }`}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Quá hạn
          </button>

          {/* Việc của tôi Toggle — task được giao cho user hiện tại */}
          <button
            onClick={() => setFilterMine(!filterMine)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
              filterMine
                ? "bg-xanh-green/15 text-xanh-deep border-xanh-green/40"
                : "bg-card text-muted-foreground border-border hover:bg-muted/30"
            }`}
          >
            <UserPlus className="h-3.5 w-3.5" />
            Việc của tôi
          </button>
        </div>
      </div>

      {/* Task List */}
      {loading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="text-center p-12 border border-border rounded-2xl bg-card text-muted-foreground shadow-sm">
          Chưa có Task nào được tự động tạo.
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => {
            const isExpanded = expandedTask === task.id;
            const childAlerts = alerts[task.id] || [];
            const overdue = isOverdue(task);
            const urgent =
              (task.priority === "P5" || task.priority === "P4") && task.status !== "resolved";
            const mineTask = !!me?.id && task.owner_id === me.id;

            return (
              <div
                key={task.id}
                className={`rounded-2xl border bg-card shadow-[var(--shadow-card)] overflow-hidden transition-all ${
                  urgent
                    ? "border-red-300 ring-1 ring-red-200 hover:border-red-400"
                    : "border-border hover:border-xanh-green/30"
                }`}
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
                        {STATUS_LABELS[task.status] ?? task.status}
                      </span>
                      {urgent && (
                        <span className="px-2 py-0.5 rounded bg-red-600 text-white text-[10px] font-mono font-bold uppercase animate-pulse">
                          Khẩn cấp
                        </span>
                      )}
                      {mineTask && (
                        <span className="px-2 py-0.5 rounded bg-xanh-green/20 text-xanh-deep text-[10px] font-mono font-bold uppercase border border-xanh-green/40">
                          Được giao cho bạn
                        </span>
                      )}
                      <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                        Phòng: {task.assigned_team}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                        {task.source === "report" ? "Từ báo cáo" : "Từ cảnh báo"}
                      </span>
                      {task.report_id && (
                        <a
                          href="/reports"
                          onClick={(e) => e.stopPropagation()}
                          className="text-[11px] text-xanh-deep underline font-mono"
                        >
                          Xem báo cáo gốc
                        </a>
                      )}
                      {task.priority && (
                        <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                          {task.priority}
                        </span>
                      )}
                      {overdue && (
                        <span className="bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded">
                          QUÁ HẠN
                        </span>
                      )}
                      {task.area && (
                        <span className="text-[11px] text-muted-foreground font-mono flex items-center gap-1">
                          <MapPin className="h-3 w-3" /> {regionLabel(task.area)}
                        </span>
                      )}
                    </div>
                    <h3 className="font-semibold text-lg text-xanh-deep leading-tight">
                      {task.title}
                    </h3>
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
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5" />
                    ) : (
                      <ChevronDown className="h-5 w-5" />
                    )}
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
                        Tiếp nhận xử lý
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          updateTaskStatus(task.id, "resolved");
                        }}
                        disabled={task.status === "resolved"}
                        className="px-4 py-2 bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1"
                      >
                        <CheckCircle2 className="h-4 w-4" /> Đánh dấu hoàn thành
                      </button>
                    </div>

                    {/* Assignment Section */}
                    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
                      <h4 className="font-semibold text-sm flex items-center gap-2 text-xanh-deep">
                        <UserPlus className="h-4 w-4" />
                        Gán task
                      </h4>

                      {/* Agent gợi ý người nhận (cân bằng tải trong phòng) */}
                      <div className="space-y-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            loadSuggestion(task.id);
                          }}
                          disabled={loadingSuggestion === task.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg border border-xanh-cyan/40 bg-xanh-cyan/10 text-xanh-deep hover:bg-xanh-cyan/20 transition-colors disabled:opacity-50"
                        >
                          {loadingSuggestion === task.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Sparkles className="h-3.5 w-3.5" />
                          )}
                          Gợi ý người nhận (AI)
                        </button>
                        {suggestion[task.id] && (
                          <div className="flex items-center justify-between gap-2 rounded-lg border border-xanh-cyan/40 bg-xanh-cyan/5 px-3 py-2">
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-xanh-deep truncate">
                                {suggestion[task.id].full_name || suggestion[task.id].email}
                              </p>
                              <p className="text-[11px] text-muted-foreground">
                                {suggestion[task.id].reason}
                              </p>
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                updateAssignForm(task.id, "owner_id", suggestion[task.id].id);
                                toast.success("Đã chọn người được gợi ý.");
                              }}
                              className="shrink-0 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-xanh-deep text-white hover:bg-xanh-deep/90 transition-colors"
                            >
                              Chọn
                            </button>
                          </div>
                        )}
                      </div>
                      {task.owner_email && (
                        <p className="text-xs text-muted-foreground font-mono">
                          Hiện tại:{" "}
                          <span className="text-xanh-green font-semibold">{task.owner_email}</span>
                        </p>
                      )}
                      <div className="flex flex-wrap items-end gap-3">
                        <div className="space-y-1">
                          <label className="text-[11px] font-mono text-muted-foreground">
                            Người nhận
                          </label>
                          <select
                            value={assignForm[task.id]?.owner_id || task.owner_id || ""}
                            onChange={(e) => updateAssignForm(task.id, "owner_id", e.target.value)}
                            className="px-3 py-2 text-xs border border-border rounded-lg bg-card focus:outline-none focus:ring-2 focus:ring-xanh-green/30 min-w-[200px]"
                          >
                            <option value="">-- Chọn người --</option>
                            {assignableUsers
                              .filter(
                                (user) =>
                                  user.role === "admin" ||
                                  user.department === task.assigned_team,
                              )
                              .map((user) => (
                                <option key={user.id} value={user.id}>
                                  {user.full_name || user.email} ({user.role})
                                </option>
                              ))}
                          </select>
                        </div>
                        <div className="space-y-1">
                          <label className="text-[11px] font-mono text-muted-foreground">
                            Hạn hoàn thành
                          </label>
                          <input
                            type="date"
                            value={
                              assignForm[task.id]?.due_at ||
                              (task.due_at ? task.due_at.split("T")[0] : "")
                            }
                            onChange={(e) => updateAssignForm(task.id, "due_at", e.target.value)}
                            className="px-3 py-2 text-xs border border-border rounded-lg bg-card focus:outline-none focus:ring-2 focus:ring-xanh-green/30"
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
                          Gán
                        </button>
                      </div>
                    </div>

                    {/* Báo cáo hoàn thành — chức năng RIÊNG, chỉ hiện cho nhân viên được giao */}
                    {mineTask && (
                      <div className="rounded-xl border border-xanh-green/40 bg-xanh-green/5 p-4 space-y-3">
                        <h4 className="font-semibold text-sm flex items-center gap-2 text-xanh-deep">
                          <ClipboardCheck className="h-4 w-4 text-xanh-green" />
                          Báo cáo hoàn thành
                        </h4>
                        <p className="text-[11px] text-muted-foreground">
                          Gửi báo cáo mức độ xử lý về cho quản lý. Đây là bước báo cáo, khác với
                          thao tác xử lý ticket.
                        </p>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[11px] font-mono text-muted-foreground">Mức độ:</span>
                          {[
                            { v: "completed", l: "Hoàn thành" },
                            { v: "partial", l: "Một phần" },
                            { v: "blocked", l: "Bị chặn" },
                          ].map((opt) => {
                            const active =
                              (reportForm[task.id]?.level || "completed") === opt.v;
                            return (
                              <button
                                key={opt.v}
                                onClick={() => updateReportForm(task.id, "level", opt.v)}
                                className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg border transition-colors ${
                                  active
                                    ? "bg-xanh-deep text-white border-xanh-deep"
                                    : "bg-card text-muted-foreground border-border hover:bg-muted/30"
                                }`}
                              >
                                {opt.l}
                              </button>
                            );
                          })}
                        </div>
                        <textarea
                          value={reportForm[task.id]?.note || ""}
                          onChange={(e) => updateReportForm(task.id, "note", e.target.value)}
                          placeholder="Mô tả những gì đã xử lý, kết quả, vướng mắc (nếu có)..."
                          className="w-full h-20 p-3 text-xs border border-border rounded-lg bg-card focus:outline-none focus:ring-2 focus:ring-xanh-green/30 resize-none"
                        />
                        <div className="flex justify-end">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              submitCompletionReport(task.id);
                            }}
                            disabled={submittingReport === task.id}
                            className="flex items-center gap-1.5 px-4 py-2 bg-xanh-green text-white rounded-lg text-xs font-semibold hover:bg-xanh-green/90 transition-colors disabled:opacity-50"
                          >
                            {submittingReport === task.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <ClipboardCheck className="h-3.5 w-3.5" />
                            )}
                            Gửi báo cáo
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Child Alerts */}
                    <div>
                      <h4 className="font-semibold text-sm flex items-center gap-2 mb-3">
                        <ShieldAlert className="h-4 w-4 text-amber-600" />
                        Danh sách Ticket liên quan ({childAlerts.length})
                      </h4>
                      {childAlerts.length === 0 ? (
                        <div className="text-xs text-muted-foreground p-4 bg-card rounded-lg border border-border">
                          Đang tải hoặc không có ticket...
                        </div>
                      ) : (
                        <div className="bg-card border border-border rounded-xl overflow-hidden divide-y divide-border">
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
