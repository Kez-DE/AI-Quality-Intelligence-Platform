// Bảng "Nhân viên đang hoạt động" + Team Leaderboard cho admin/manager (port từ Customer Hub Proaaa).
// Admin: /api/users (tất cả). Manager: /api/users/assignable (staff cùng phòng ban).
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ROLE_LABELS, type Me, type Role } from "@/lib/api";
import { isStaffRole } from "@/lib/access";
import { Users, Target } from "lucide-react";

type UserRow = {
  id: string;
  email: string | null;
  full_name?: string | null;
  role: Role;
  department: string | null;
};

type LeaderRow = { team: string; resolved_count: number; avg_resolution_hours: number };

// Không có presence realtime → suy ra trạng thái ổn định theo id (chỉ báo demo).
function deriveStatus(id: string): "online" | "idle" | "off" {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const m = h % 3;
  return m === 0 ? "online" : m === 1 ? "idle" : "off";
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  return (
    parts
      .map((w) => w[0])
      .slice(-2)
      .join("")
      .toUpperCase() || "U"
  );
}

function Panel({
  icon: Icon,
  title,
  sub,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  sub?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-3xl border border-border bg-card/80 p-5 shadow-sm backdrop-blur">
      <header className="mb-4 flex items-start gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15 text-primary">
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-base font-bold leading-tight">{title}</h3>
          {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
        </div>
      </header>
      {children}
    </section>
  );
}

const STATUS_STYLE: Record<string, string> = {
  online: "bg-success",
  idle: "bg-warning",
  off: "bg-muted-foreground",
};

export default function EmployeesPanel({ me }: { me: Me }) {
  const isAdmin = me.role === "admin";

  const usersQuery = useQuery({
    queryKey: ["employees-panel", me.role, me.department],
    queryFn: () =>
      isAdmin
        ? apiFetch<{ data: UserRow[] }>("/api/users")
        : apiFetch<{ data: UserRow[] }>(
            `/api/users/assignable${me.department ? `?team=${encodeURIComponent(me.department)}` : ""}`,
          ),
    staleTime: 30_000,
    retry: false,
  });

  const lbQuery = useQuery({
    queryKey: ["leaderboard-panel"],
    queryFn: () => apiFetch<{ data: LeaderRow[] }>("/api/leaderboard"),
    staleTime: 30_000,
    retry: false,
  });

  // Staff roles only: /api/users also returns Pending and Customer accounts (US-078).
  const employees = (usersQuery.data?.data || []).filter((u) => isStaffRole(u.role));
  const leaders = lbQuery.data?.data || [];

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[360px_1fr]">
      {/* Team Leaderboard */}
      <Panel icon={Target} title="Team Leaderboard" sub="Top tốc độ xử lý & số task hoàn thành">
        {leaders.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            {lbQuery.isLoading ? "Đang tải…" : "Chưa có task hoàn thành để xếp hạng."}
          </p>
        ) : (
          <ul className="space-y-2">
            {leaders.slice(0, 6).map((r, i) => (
              <li
                key={r.team}
                className="flex items-center gap-3 rounded-xl border border-border bg-card/70 p-3"
              >
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary/15 text-xs font-bold text-primary">
                  #{i + 1}
                </span>
                <div className="min-w-0 flex-1 leading-tight">
                  <div className="truncate text-sm font-semibold">{r.team}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {r.resolved_count} task · avg time
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold">{r.avg_resolution_hours}h</div>
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    avg time
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {/* Active employees */}
      <Panel
        icon={Users}
        title="Nhân viên đang hoạt động"
        sub={
          isAdmin
            ? "Toàn bộ tài khoản vận hành · phân quyền theo vai trò"
            : `Nhân viên phòng ${me.department ?? "—"}`
        }
      >
        {employees.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            {usersQuery.isLoading
              ? "Đang tải…"
              : usersQuery.isError
                ? "Không tải được danh sách."
                : "Chưa có nhân viên."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="py-2 font-medium">Người dùng</th>
                  <th className="py-2 font-medium">Vai trò</th>
                  <th className="py-2 font-medium">Phòng ban</th>
                  <th className="py-2 font-medium">Trạng thái</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {employees.map((u) => {
                  const name = u.full_name || (u.email ? u.email.split("@")[0] : "—");
                  const status = deriveStatus(u.id);
                  return (
                    <tr key={u.id}>
                      <td className="py-3">
                        <div className="flex items-center gap-3">
                          <span className="grid h-8 w-8 place-items-center rounded-full bg-primary/15 text-[11px] font-bold text-primary">
                            {initials(name)}
                          </span>
                          <div className="leading-tight">
                            <div className="font-medium">{name}</div>
                            <div className="text-[11px] text-muted-foreground">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3">
                        <span className="inline-flex items-center rounded-md border border-primary/20 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-foreground/80">
                          {ROLE_LABELS[u.role] ?? u.role}
                        </span>
                      </td>
                      <td className="py-3 text-muted-foreground">{u.department ?? "—"}</td>
                      <td className="py-3">
                        <span className="inline-flex items-center gap-1.5 text-xs">
                          <span className={`h-1.5 w-1.5 rounded-full ${STATUS_STYLE[status]}`} />
                          {status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
