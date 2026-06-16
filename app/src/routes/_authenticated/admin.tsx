import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, useMe, ROLE_LABELS, type Role } from "@/lib/api";
import { Loader2, ShieldAlert, Trash2, Users, CheckCircle, Shield } from "lucide-react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const Route = createFileRoute("/_authenticated/admin")({
  component: AdminPage,
});

type ManagedUser = {
  id: string;
  email: string | null;
  full_name: string | null;
  role: Role;
  created_at: string;
};

const ROLES: Role[] = ["admin", "manager", "staff", "guest"];

function getRoleBadgeColor(role: Role) {
  switch (role) {
    case "admin": return "bg-red-100 text-red-800 border-red-200";
    case "manager": return "bg-blue-100 text-blue-800 border-blue-200";
    case "staff": return "bg-gray-100 text-gray-800 border-gray-200";
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
  const activeUsers = allUsers.filter(u => u.role !== "guest");

  const renderTable = (users: ManagedUser[], isPendingTab: boolean) => (
    <div className="rounded-2xl border border-border bg-white shadow-[var(--shadow-card)] overflow-hidden">
      <div className="grid grid-cols-12 gap-3 px-5 py-3 border-b border-border bg-muted/40 text-xs font-mono uppercase text-muted-foreground">
        <span className="col-span-4">Người dùng</span>
        <span className="col-span-3">Quyền</span>
        <span className="col-span-2">Ngày tham gia</span>
        <span className="col-span-3 text-right">Thao tác</span>
      </div>
      <div className="divide-y divide-border">
        {users.length === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">
            Không có tài khoản nào.
          </div>
        )}
        {users.map((u) => {
          const isSelf = u.id === me.data?.id;
          const busy = pendingId === u.id;
          return (
            <div key={u.id} className="grid grid-cols-12 gap-3 px-5 py-3 items-center text-sm">
              <div className="col-span-4 min-w-0">
                <div className="font-semibold truncate">{u.full_name || "—"}</div>
                <div className="text-xs font-mono text-muted-foreground truncate">{u.email}</div>
              </div>
              <div className="col-span-3 flex items-center gap-2">
                {isPendingTab ? (
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${getRoleBadgeColor(u.role)}`}>
                    Chờ duyệt
                  </span>
                ) : (
                  <select
                    value={u.role}
                    disabled={busy}
                    onChange={(e) => {
                      setPendingId(u.id);
                      roleMutation.mutate({ id: u.id, role: e.target.value as Role });
                    }}
                    className="h-9 px-2 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-xanh-green/40 disabled:opacity-60"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {ROLE_LABELS[r]}
                      </option>
                    ))}
                  </select>
                )}
                {isSelf && <span className="text-[10px] font-mono text-muted-foreground">(bạn)</span>}
              </div>
              <div className="col-span-2 text-xs text-muted-foreground">
                {new Date(u.created_at).toLocaleDateString("vi-VN")}
              </div>
              <div className="col-span-3 flex justify-end gap-2">
                {isPendingTab ? (
                  <>
                    <button
                      disabled={busy}
                      onClick={() => {
                        setPendingId(u.id);
                        roleMutation.mutate({ id: u.id, role: "staff" });
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-xanh-green/10 text-xanh-green text-xs font-semibold hover:bg-xanh-green/20 disabled:opacity-40 transition-colors"
                      title="Duyệt cấp quyền Nhân viên"
                    >
                      {busy && pendingId === u.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
                      Duyệt Staff
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => {
                        setPendingId(u.id);
                        roleMutation.mutate({ id: u.id, role: "manager" });
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-100 text-blue-700 text-xs font-semibold hover:bg-blue-200 disabled:opacity-40 transition-colors"
                      title="Duyệt cấp quyền Quản lý"
                    >
                      {busy && pendingId === u.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Shield className="h-3.5 w-3.5" />}
                      Duyệt Manager
                    </button>
                  </>
                ) : null}
                <button
                  disabled={busy || isSelf}
                  title={isSelf ? "Không thể tự xoá tài khoản đang đăng nhập" : "Xoá tài khoản"}
                  onClick={() => {
                    if (!window.confirm(`Xoá tài khoản ${u.email}? Hành động không thể hoàn tác.`)) return;
                    setPendingId(u.id);
                    deleteMutation.mutate(u.id);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-xanh-coral/10 text-xanh-coral text-xs font-semibold hover:bg-xanh-coral/20 disabled:opacity-40 transition-colors"
                >
                  {busy && pendingId === u.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
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
      <div className="flex items-center gap-2">
        <Users className="h-7 w-7 text-xanh-deep" />
        <div>
          <h1 className="font-display text-3xl font-bold">Quản lý người dùng</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Phân quyền và duyệt tài khoản trong hệ thống.
          </p>
        </div>
      </div>

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
          <TabsList className="mb-4">
            <TabsTrigger value="pending" className="relative">
              Chờ duyệt
              {pendingUsers.length > 0 && (
                <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold text-white bg-xanh-coral rounded-full">
                  {pendingUsers.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="active">Đã phân quyền ({activeUsers.length})</TabsTrigger>
          </TabsList>
          
          <TabsContent value="pending" className="mt-0 outline-none">
            {renderTable(pendingUsers, true)}
          </TabsContent>
          
          <TabsContent value="active" className="mt-0 outline-none">
            {renderTable(activeUsers, false)}
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
