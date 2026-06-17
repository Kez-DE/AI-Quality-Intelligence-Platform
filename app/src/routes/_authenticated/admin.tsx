import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, useMe, ROLE_LABELS, type Role } from "@/lib/api";
import {
  Loader2, ShieldAlert, Trash2, Users, CheckCircle, Shield, UserCheck,
  UserCog, Clock, Radio, Play, Square, RefreshCw, RotateCcw, Activity,
} from "lucide-react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// ---- Live Stream Types ----
type LiveStreamStatus = {
  running: boolean;
  offset: number;
  batch_size: number;
  interval_seconds: number;
  loop: boolean;
  auto_ticket: boolean;
  ticket_every_batches: number;
  batches_ingested: number;
  ticket_running: boolean;
  last_result: { inserted: number; skipped: number; complete: boolean } | null;
  last_error: string | null;
  last_ticket_at: string | null;
  last_ticket_result: unknown;
  last_ticket_error: string | null;
};

function LiveStreamPanel() {
  const qc = useQueryClient();
  const [batchSize, setBatchSize] = useState(150);
  const [interval, setIntervalSec] = useState(10);
  const [loop, setLoop] = useState(false);
  const [reset, setReset] = useState(false);
  const [autoTicket, setAutoTicket] = useState(true);
  const [ticketEvery, setTicketEvery] = useState(10);

  const statusQuery = useQuery({
    queryKey: ["live-stream-status"],
    queryFn: async () => {
      const json = await apiFetch<{ data: LiveStreamStatus }>("/api/live-stream/status");
      return json.data;
    },
    refetchInterval: 5_000,
  });

  const startMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({
        batch_size: String(batchSize),
        interval_seconds: String(interval),
        loop: String(loop),
        reset: String(reset),
        auto_ticket: String(autoTicket),
        ticket_every_batches: String(ticketEvery),
      });
      await apiFetch(`/api/live-stream/start?${params}`, { method: "POST" });
    },
    onSuccess: () => {
      toast.success("Live stream đã bật");
      qc.invalidateQueries({ queryKey: ["live-stream-status"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Không thể bật live stream"),
  });

  const stopMutation = useMutation({
    mutationFn: async () => {
      await apiFetch("/api/live-stream/stop", { method: "POST" });
    },
    onSuccess: () => {
      toast.success("Live stream đã tắt");
      qc.invalidateQueries({ queryKey: ["live-stream-status"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Không thể tắt live stream"),
  });

  const s = statusQuery.data;
  const isRunning = s?.running ?? false;
  const isBusy = startMutation.isPending || stopMutation.isPending;

  return (
    <div className="space-y-5">
      {/* Status bar */}
      <div className={`rounded-xl border p-4 flex flex-wrap items-center gap-4 ${isRunning ? "border-emerald-200 bg-emerald-50" : "border-gray-200 bg-gray-50"}`}>
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${isRunning ? "bg-emerald-500 animate-pulse" : "bg-gray-400"}`} />
          <span className="text-sm font-semibold">{isRunning ? "Đang chạy" : "Đã dừng"}</span>
        </div>
        {s && (
          <>
            <span className="text-xs text-muted-foreground">Batch {s.batches_ingested} · offset {s.offset}</span>
            {s.last_result && (
              <span className="text-xs text-muted-foreground">
                Batch cuối: +{s.last_result.inserted} inserted, {s.last_result.skipped} skipped
                {s.last_result.complete && " · ✅ Hết data"}
              </span>
            )}
            {s.last_error && (
              <span className="text-xs text-red-600 font-mono">Lỗi: {s.last_error}</span>
            )}
          </>
        )}
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ["live-stream-status"] })}
          className="ml-auto text-muted-foreground hover:text-foreground transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Config + controls */}
      <div className="rounded-xl border border-border bg-white p-5 space-y-4">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Activity className="h-4 w-4" /> Cấu hình
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <label className="space-y-1">
            <span className="text-xs text-muted-foreground">Batch size</span>
            <input
              type="number" min={10} max={500} value={batchSize}
              onChange={e => setBatchSize(Number(e.target.value))}
              disabled={isRunning}
              className="w-full h-8 px-2 rounded-lg border border-border text-sm focus:outline-none focus:ring-2 focus:ring-xanh-green/40 disabled:opacity-50"
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs text-muted-foreground">Interval (giây)</span>
            <input
              type="number" min={1} max={3600} value={interval}
              onChange={e => setIntervalSec(Number(e.target.value))}
              disabled={isRunning}
              className="w-full h-8 px-2 rounded-lg border border-border text-sm focus:outline-none focus:ring-2 focus:ring-xanh-green/40 disabled:opacity-50"
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs text-muted-foreground">Ticket mỗi N batch</span>
            <input
              type="number" min={1} max={100} value={ticketEvery}
              onChange={e => setTicketEvery(Number(e.target.value))}
              disabled={isRunning}
              className="w-full h-8 px-2 rounded-lg border border-border text-sm focus:outline-none focus:ring-2 focus:ring-xanh-green/40 disabled:opacity-50"
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="checkbox" checked={loop} onChange={e => setLoop(e.target.checked)} disabled={isRunning}
              className="rounded border-gray-300 text-xanh-green focus:ring-xanh-green/40" />
            Lặp lại (loop)
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="checkbox" checked={autoTicket} onChange={e => setAutoTicket(e.target.checked)} disabled={isRunning}
              className="rounded border-gray-300 text-xanh-green focus:ring-xanh-green/40" />
            Tự tạo ticket
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="checkbox" checked={reset} onChange={e => setReset(e.target.checked)} disabled={isRunning}
              className="rounded border-gray-300 text-xanh-green focus:ring-xanh-green/40" />
            Reset offset khi bật
          </label>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3 pt-1">
          {!isRunning ? (
            <button
              disabled={isBusy}
              onClick={() => startMutation.mutate()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-500 text-white text-sm font-semibold hover:bg-emerald-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Bật Live Stream
            </button>
          ) : (
            <button
              disabled={isBusy}
              onClick={() => {
                if (!window.confirm("Tắt live stream? Dữ liệu đang ingest sẽ dừng lại.")) return;
                stopMutation.mutate();
              }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
              Dừng Live Stream
            </button>
          )}
          {!isRunning && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <RotateCcw className="h-3 w-3" />
              {reset ? "Sẽ reset offset về 0 khi bật" : "Tiếp tục từ offset hiện tại"}
            </span>
          )}
        </div>
      </div>

      {/* Ticket detection status */}
      {s?.last_ticket_at && (
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm space-y-1">
          <div className="font-semibold text-blue-800 flex items-center gap-2">
            <Activity className="h-4 w-4" /> Spike Detection cuối
          </div>
          <div className="text-xs text-blue-700">
            {new Date(s.last_ticket_at).toLocaleString("vi-VN")}
            {s.ticket_running && <span className="ml-2 text-blue-500 animate-pulse">· đang chạy...</span>}
          </div>
          {s.last_ticket_error && (
            <div className="text-xs text-red-600 font-mono">Lỗi: {s.last_ticket_error}</div>
          )}
        </div>
      )}
    </div>
  );
}

export const Route = createFileRoute("/_authenticated/admin")({
  component: AdminPage,
});

type ManagedUser = {
  id: string;
  email: string | null;
  full_name: string | null;
  role: Role;
  department: string | null;
  created_at: string;
};

const ROLES: Role[] = ["admin", "manager", "staff", "guest"];
const DEPARTMENTS = ["IT", "Safety", "CSKH", "Vận hành", "Pricing", "Marketing"] as const;

function getRoleBadgeColor(role: Role) {
  switch (role) {
    case "admin": return "bg-red-100 text-red-800 border-red-200";
    case "manager": return "bg-blue-100 text-blue-800 border-blue-200";
    case "staff": return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "guest": return "bg-yellow-100 text-yellow-800 border-yellow-200";
    default: return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

function AdminPage() {
  const me = useMe();
  const qc = useQueryClient();
  const [pendingId, setPendingId] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const json = await apiFetch<{ data: ManagedUser[] }>("/api/users");
      return json.data;
    },
    enabled: me.data?.role === "admin",
    retry: false,
  });

  const roleMutation = useMutation({
    mutationFn: async ({ id, role }: { id: string; role: Role }) => {
      await apiFetch(`/api/users/${id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
    },
    onSuccess: () => {
      toast.success("Đã cập nhật quyền");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Cập nhật thất bại"),
    onSettled: () => setPendingId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiFetch(`/api/users/${id}`, { method: "DELETE" });
    },
    onSuccess: () => {
      toast.success("Đã xoá tài khoản");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Xoá thất bại"),
    onSettled: () => setPendingId(null),
  });

  const departmentMutation = useMutation({
    mutationFn: async ({ id, department }: { id: string; department: string | null }) => {
      await apiFetch(`/api/users/${id}/department`, {
        method: "PATCH",
        body: JSON.stringify({ department }),
      });
    },
    onSuccess: () => {
      toast.success("Đã cập nhật phòng ban");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Cập nhật phòng ban thất bại"),
    onSettled: () => setPendingId(null),
  });

  if (me.isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
      </div>
    );
  }

  if (me.data?.role !== "admin") {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <ShieldAlert className="h-12 w-12 mx-auto text-xanh-coral mb-3" />
        <h1 className="font-display text-2xl font-bold">Không đủ quyền truy cập</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Trang quản lý người dùng chỉ dành cho quản trị viên. Quyền hiện tại của bạn:{" "}
          <strong>{me.data ? ROLE_LABELS[me.data.role] : "không xác định"}</strong>.
        </p>
      </div>
    );
  }

  const allUsers = usersQuery.data ?? [];
  const pendingUsers = allUsers.filter(u => u.role === "guest");
  const managerUsers = allUsers.filter(u => u.role === "manager");
  const staffUsers = allUsers.filter(u => u.role === "staff");
  const adminUsers = allUsers.filter(u => u.role === "admin");

  // --- Card-based pending user ---
  const renderPendingCards = () => (
    <div className="space-y-3">
      {pendingUsers.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-muted/30 py-12 text-center">
          <CheckCircle className="h-10 w-10 mx-auto text-xanh-green/60 mb-3" />
          <p className="text-sm text-muted-foreground font-medium">Không có tài khoản nào chờ duyệt</p>
          <p className="text-xs text-muted-foreground mt-1">Tất cả đã được xử lý.</p>
        </div>
      ) : (
        pendingUsers.map((u) => {
          const busy = pendingId === u.id;
          return (
            <div key={u.id} className="rounded-xl border border-yellow-200 bg-yellow-50/50 p-4 flex flex-col sm:flex-row sm:items-center gap-4 transition-all hover:shadow-md">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-yellow-100 border border-yellow-200 flex items-center justify-center">
                  <Clock className="h-5 w-5 text-yellow-600" />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-sm truncate">{u.full_name || "Chưa có tên"}</div>
                  <div className="text-xs text-muted-foreground font-mono truncate">{u.email}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    Đăng ký: {new Date(u.created_at).toLocaleDateString("vi-VN")}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  disabled={busy}
                  onClick={() => {
                    setPendingId(u.id);
                    roleMutation.mutate({ id: u.id, role: "staff" });
                  }}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-500 text-white text-xs font-semibold hover:bg-emerald-600 disabled:opacity-40 transition-colors shadow-sm"
                  title="Duyệt thành Nhân viên"
                >
                  {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserCheck className="h-3.5 w-3.5" />}
                  Duyệt Nhân viên
                </button>
                <button
                  disabled={busy}
                  onClick={() => {
                    setPendingId(u.id);
                    roleMutation.mutate({ id: u.id, role: "manager" });
                  }}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-blue-500 text-white text-xs font-semibold hover:bg-blue-600 disabled:opacity-40 transition-colors shadow-sm"
                  title="Duyệt thành Quản lý"
                >
                  {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Shield className="h-3.5 w-3.5" />}
                  Duyệt Quản lý
                </button>
                <button
                  disabled={busy}
                  title="Từ chối và xoá tài khoản"
                  onClick={() => {
                    if (!window.confirm(`Từ chối và xoá tài khoản ${u.email}? Hành động không thể hoàn tác.`)) return;
                    setPendingId(u.id);
                    deleteMutation.mutate(u.id);
                  }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-50 text-red-600 text-xs font-semibold hover:bg-red-100 border border-red-200 disabled:opacity-40 transition-colors"
                >
                  {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                  Từ chối
                </button>
              </div>
            </div>
          );
        })
      )}
    </div>
  );

  // --- Table for active users (manager/staff/admin) ---
  const renderActiveTable = (users: ManagedUser[]) => (
    <div className="rounded-2xl border border-border bg-white shadow-sm overflow-hidden">
      <div className="grid grid-cols-12 gap-3 px-5 py-3 border-b border-border bg-muted/40 text-xs font-semibold uppercase text-muted-foreground tracking-wide">
        <span className="col-span-3">Người dùng</span>
        <span className="col-span-2">Vai trò</span>
        <span className="col-span-2">Phòng ban</span>
        <span className="col-span-2">Ngày tham gia</span>
        <span className="col-span-3 text-right">Thao tác</span>
      </div>
      <div className="divide-y divide-border">
        {users.length === 0 && (
          <div className="py-10 text-center text-sm text-muted-foreground">
            Không có tài khoản nào trong nhóm này.
          </div>
        )}
        {users.map((u) => {
          const isSelf = u.id === me.data?.id;
          const busy = pendingId === u.id;
          return (
            <div key={u.id} className="grid grid-cols-12 gap-3 px-5 py-3.5 items-center text-sm hover:bg-muted/20 transition-colors">
              <div className="col-span-3 min-w-0">
                <div className="font-semibold truncate">
                  {u.full_name || "—"}
                  {isSelf && <span className="ml-1.5 text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">(bạn)</span>}
                </div>
                <div className="text-xs font-mono text-muted-foreground truncate">{u.email}</div>
              </div>
              <div className="col-span-2">
                <select
                  value={u.role}
                  disabled={busy || isSelf}
                  onChange={(e) => {
                    setPendingId(u.id);
                    roleMutation.mutate({ id: u.id, role: e.target.value as Role });
                  }}
                  className="h-8 px-2 rounded-lg border border-border bg-white text-xs font-medium focus:outline-none focus:ring-2 focus:ring-xanh-green/40 disabled:opacity-60 w-full"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {ROLE_LABELS[r]}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-span-2">
                <select
                  value={u.department ?? ""}
                  disabled={busy}
                  onChange={(e) => {
                    setPendingId(u.id);
                    departmentMutation.mutate({ id: u.id, department: e.target.value || null });
                  }}
                  className="h-8 px-2 rounded-lg border border-border bg-white text-xs font-medium focus:outline-none focus:ring-2 focus:ring-xanh-green/40 disabled:opacity-60 w-full"
                >
                  <option value="">Chưa gán</option>
                  {DEPARTMENTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="col-span-2 text-xs text-muted-foreground">
                {new Date(u.created_at).toLocaleDateString("vi-VN")}
              </div>
              <div className="col-span-3 flex justify-end">
                <button
                  disabled={busy || isSelf}
                  title={isSelf ? "Không thể tự xoá tài khoản đang đăng nhập" : "Xoá tài khoản"}
                  onClick={() => {
                    if (!window.confirm(`Xoá tài khoản ${u.email}? Hành động không thể hoàn tác.`)) return;
                    setPendingId(u.id);
                    deleteMutation.mutate(u.id);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-red-600 text-xs font-semibold hover:bg-red-50 border border-transparent hover:border-red-200 disabled:opacity-40 transition-colors"
                >
                  {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                  Xoá
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-xanh-deep/10 flex items-center justify-center">
          <Users className="h-6 w-6 text-xanh-deep" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold">Quản lý người dùng</h1>
          <p className="text-sm text-muted-foreground">
            Phân quyền, duyệt tài khoản và quản lý nhân sự trong hệ thống.
          </p>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-3.5">
          <div className="text-2xl font-bold text-yellow-700">{pendingUsers.length}</div>
          <div className="text-xs text-yellow-600 font-medium mt-0.5">Chờ duyệt</div>
        </div>
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-3.5">
          <div className="text-2xl font-bold text-blue-700">{managerUsers.length}</div>
          <div className="text-xs text-blue-600 font-medium mt-0.5">Quản lý</div>
        </div>
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3.5">
          <div className="text-2xl font-bold text-emerald-700">{staffUsers.length}</div>
          <div className="text-xs text-emerald-600 font-medium mt-0.5">Nhân viên</div>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50 p-3.5">
          <div className="text-2xl font-bold text-red-700">{adminUsers.length}</div>
          <div className="text-xs text-red-600 font-medium mt-0.5">Quản trị viên</div>
        </div>
      </div>

      {/* Content */}
      {usersQuery.isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
        </div>
      ) : usersQuery.isError ? (
        <div className="text-center py-16 text-xanh-coral">
          {usersQuery.error instanceof Error ? usersQuery.error.message : "Không tải được danh sách"}
        </div>
      ) : (
        <Tabs defaultValue="pending" className="w-full">
          <TabsList className="mb-4 bg-muted/60 p-1 rounded-xl">
            <TabsTrigger value="pending" className="rounded-lg gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Clock className="h-3.5 w-3.5" />
              Chờ duyệt
              {pendingUsers.length > 0 && (
                <span className="ml-1 inline-flex items-center justify-center min-w-5 h-5 px-1.5 text-[10px] font-bold text-white bg-xanh-coral rounded-full">
                  {pendingUsers.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="manager" className="rounded-lg gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Shield className="h-3.5 w-3.5" />
              Quản lý
              <span className="ml-1 text-[10px] text-muted-foreground">({managerUsers.length})</span>
            </TabsTrigger>
            <TabsTrigger value="staff" className="rounded-lg gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <UserCheck className="h-3.5 w-3.5" />
              Nhân viên
              <span className="ml-1 text-[10px] text-muted-foreground">({staffUsers.length})</span>
            </TabsTrigger>
            <TabsTrigger value="admin" className="rounded-lg gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <UserCog className="h-3.5 w-3.5" />
              Quản trị viên
              <span className="ml-1 text-[10px] text-muted-foreground">({adminUsers.length})</span>
            </TabsTrigger>
            <TabsTrigger value="livestream" className="rounded-lg gap-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Radio className="h-3.5 w-3.5" />
              Live Stream
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pending" className="mt-0 outline-none">
            {renderPendingCards()}
          </TabsContent>

          <TabsContent value="manager" className="mt-0 outline-none">
            {renderActiveTable(managerUsers)}
          </TabsContent>

          <TabsContent value="staff" className="mt-0 outline-none">
            {renderActiveTable(staffUsers)}
          </TabsContent>

          <TabsContent value="admin" className="mt-0 outline-none">
            {renderActiveTable(adminUsers)}
          </TabsContent>

          <TabsContent value="livestream" className="mt-0 outline-none">
            <LiveStreamPanel />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
