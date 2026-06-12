import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, useMe, ROLE_LABELS, type Role } from "@/lib/api";
import { Loader2, ShieldAlert, Trash2, Users } from "lucide-react";
import { toast } from "sonner";

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

  // Gate: chỉ admin được vào. Chờ /api/me trả về trước khi quyết định.
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

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Users className="h-7 w-7 text-xanh-deep" />
        <div>
          <h1 className="font-display text-3xl font-bold">Quản lý người dùng</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Phân quyền và quản lý tài khoản trong hệ thống.
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
        <div className="rounded-2xl border border-border bg-white shadow-[var(--shadow-card)] overflow-hidden">
          <div className="grid grid-cols-12 gap-3 px-5 py-3 border-b border-border bg-muted/40 text-xs font-mono uppercase text-muted-foreground">
            <span className="col-span-4">Người dùng</span>
            <span className="col-span-3">Quyền</span>
            <span className="col-span-3">Ngày tạo</span>
            <span className="col-span-2 text-right">Thao tác</span>
          </div>
          <div className="divide-y divide-border">
            {(usersQuery.data ?? []).map((u) => {
              const isSelf = u.id === me.data?.id;
              const busy = pendingId === u.id;
              return (
                <div key={u.id} className="grid grid-cols-12 gap-3 px-5 py-3 items-center text-sm">
                  <div className="col-span-4 min-w-0">
                    <div className="font-semibold truncate">{u.full_name || "—"}</div>
                    <div className="text-xs font-mono text-muted-foreground truncate">{u.email}</div>
                  </div>
                  <div className="col-span-3">
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
                    {isSelf && <span className="ml-2 text-[10px] font-mono text-muted-foreground">(bạn)</span>}
                  </div>
                  <div className="col-span-3 text-xs text-muted-foreground">
                    {new Date(u.created_at).toLocaleDateString("vi-VN")}
                  </div>
                  <div className="col-span-2 flex justify-end">
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
                      {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                      Xoá
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
