import { Link, useRouter, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useMe, ROLE_LABELS } from "@/lib/api";
import { useRealtimeNotifications } from "@/hooks/useRealtimeNotifications";
import NotificationPanel from "@/components/NotificationPanel";
import {
  Bell,
  Building2,
  Car,
  FileText,
  Gauge,
  Kanban,
  LogOut,
  MessageSquare,
  Shield,
  Sparkles,
  User as UserIcon,
  HeartPulse,
} from "lucide-react";
import { toast } from "sonner";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge },
  { to: "/alerts", label: "Ticket Triage 🔴", icon: Bell },
  { to: "/tasks", label: "Task Manager", icon: Kanban },
  { to: "/feedback", label: "Phản hồi", icon: MessageSquare },
  { to: "/reports", label: "Báo cáo AI", icon: FileText },
  { to: "/insights", label: "Phân tích phòng ban", icon: Building2 },
  { to: "/chat", label: "AI Chat", icon: Sparkles },
];

// Link chỉ hiện với admin.
const ADMIN_NAV = { to: "/admin", label: "Quản lý người dùng", icon: Shield } as const;
// Link hiện cho ops staff (staff/manager/admin).
const HEALTH_NAV = { to: "/system-health", label: "System Health", icon: HeartPulse } as const;

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [email, setEmail] = useState<string>("");
  const { data: me } = useMe();

  const role = me?.role || "guest";
  const { notifications, unreadCount, markAsRead, markAllRead } = useRealtimeNotifications();

  const navItems = NAV.map(n => {
    if (n.to === "/chat" && role === "guest") {
      return { ...n, label: "Hỗ trợ CSKH" };
    }
    return n;
  }).filter(n => {
    if (role === "guest" && ["/alerts", "/insights", "/tasks", "/reports"].includes(n.to)) return false;
    if (role === "staff" && ["/reports"].includes(n.to)) return false;
    return true;
  });

  if (role === "admin") {
    navItems.push(ADMIN_NAV);
  }
  if (["admin", "manager", "staff"].includes(role)) {
    navItems.push(HEALTH_NAV);
  }

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? "");
    });
  }, []);

  async function signOut() {
    await supabase.auth.signOut();
    toast.success("Đã đăng xuất");
    router.navigate({ to: "/auth", replace: true });
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-border bg-white/80 backdrop-blur sticky top-0 h-screen">
        <div className="p-5 border-b border-border">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div
              className="h-9 w-9 rounded-xl grid place-items-center text-white shadow-[var(--shadow-green)]"
              style={{ background: "var(--gradient-green)" }}
            >
              <Car className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <div className="font-display font-bold text-sm">xanhSM Cockpit</div>
              <div className="text-[10px] font-mono text-muted-foreground">
                AI Quality Intel.
              </div>
            </div>
          </Link>
        </div>
        {role !== "guest" && (
          <div className="px-3 pt-3">
            <NotificationPanel
              notifications={notifications}
              unreadCount={unreadCount}
              onMarkRead={markAsRead}
              onMarkAllRead={markAllRead}
            />
          </div>
        )}
        <nav className="p-3 flex-1 space-y-1">
          {navItems.map((n) => {
            const Icon = n.icon;
            const active = pathname === n.to;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                  active
                    ? "bg-xanh-mint text-xanh-deep font-semibold shadow-sm"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-border space-y-2">
          <div className="flex items-center gap-2 px-2 py-1.5 text-xs">
            <div className="h-7 w-7 rounded-full bg-xanh-mint grid place-items-center">
              <UserIcon className="h-3.5 w-3.5 text-xanh-deep" />
            </div>
            <div className="min-w-0 leading-tight">
              <div className="truncate font-mono text-muted-foreground">{email}</div>
              {me?.role && (
                <div className="text-[10px] font-semibold text-xanh-deep">{ROLE_LABELS[me.role]}</div>
              )}
            </div>
          </div>
          <button
            onClick={signOut}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg text-muted-foreground hover:bg-xanh-coral/10 hover:text-xanh-coral transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 inset-x-0 z-40 bg-white/90 backdrop-blur border-b border-border">
        <div className="flex items-center justify-between px-3 h-14">
          <div className="flex items-center gap-2">
            <div
              className="h-8 w-8 rounded-lg grid place-items-center text-white"
              style={{ background: "var(--gradient-green)" }}
            >
              <Car className="h-4 w-4" />
            </div>
            <span className="font-display font-bold text-sm">xanhSM</span>
          </div>
          <div className="flex items-center gap-2">
            {role !== "guest" && (
              <NotificationPanel
                notifications={notifications}
                unreadCount={unreadCount}
                onMarkRead={markAsRead}
                onMarkAllRead={markAllRead}
              />
            )}
            <button onClick={signOut} className="text-xs font-mono text-muted-foreground">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="flex overflow-x-auto px-2 pb-2 gap-1">
          {navItems.map((n) => {
            const Icon = n.icon;
            const active = pathname === n.to;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap ${
                  active ? "bg-xanh-deep text-white" : "bg-muted text-muted-foreground"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {n.label}
              </Link>
            );
          })}
        </div>
      </div>

      <main className="flex-1 md:py-6 md:px-8 pt-28 pb-10 px-4 max-w-7xl">{children}</main>
    </div>
  );
}
