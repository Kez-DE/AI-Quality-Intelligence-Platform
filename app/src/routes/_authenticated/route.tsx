import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { supabase } from "@/integrations/supabase/client";
import AppShell from "@/components/AppShell";

export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: async ({ location }) => {
    const { data: sessionData } = await supabase.auth.getSession();
    if (!sessionData.session) throw redirect({ to: "/auth" });

    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) throw redirect({ to: "/auth" });

    let role = "guest";
    try {
      const { data: profile } = await supabase
        .from("profiles")
        .select("role")
        .eq("id", data.user.id)
        .maybeSingle();

      role = profile?.role || "guest";
    } catch {
      role = "guest";
    }

    // Route Guard for Guests — Khách chỉ dùng Dashboard (đã gồm form phản hồi + trợ lý CSKH nổi).
    const restrictedForGuests = [
      "/alerts",
      "/insights",
      "/admin",
      "/tasks",
      "/reports",
      "/completion-reports",
      "/support",
      "/live-stream",
      "/feedback",
      "/chat",
    ];
    if (role === "guest" && restrictedForGuests.some((p) => location.pathname.startsWith(p))) {
      throw redirect({ to: "/dashboard" });
    }

    // Route Guard for Staff/Manager
    if ((role === "staff" || role === "manager") && location.pathname.startsWith("/admin")) {
      throw redirect({ to: "/dashboard" });
    }

    // Phân tích & báo cáo là việc của quản lý/admin. Nhân viên tập trung xử lý phản hồi + task.
    const managerOnlyForStaff = ["/insights", "/reports", "/completion-reports"];
    if (role === "staff" && managerOnlyForStaff.some((p) => location.pathname.startsWith(p))) {
      throw redirect({ to: "/dashboard" });
    }

    return { user: data.user, role };
  },
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
});
