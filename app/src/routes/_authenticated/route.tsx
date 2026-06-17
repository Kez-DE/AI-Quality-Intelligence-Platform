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

    // Routes giới hạn theo role
    const guestOnly    = ["/dashboard", "/feedback", "/chat", "/auth"];
    const staffAndUp   = ["/alerts", "/tasks", "/insights", "/system-health"];
    const managerAndUp = ["/reports"];
    const adminOnly    = ["/admin"];

    if (role === "guest") {
      const allowed = ["/dashboard", "/feedback", "/chat"];
      if (!allowed.some(p => location.pathname.startsWith(p))) {
        throw redirect({ to: "/dashboard" });
      }
    } else if (role === "staff") {
      if (managerAndUp.some(p => location.pathname.startsWith(p)) ||
          adminOnly.some(p => location.pathname.startsWith(p))) {
        throw redirect({ to: "/dashboard" });
      }
    } else if (role === "manager") {
      if (adminOnly.some(p => location.pathname.startsWith(p))) {
        throw redirect({ to: "/dashboard" });
      }
    }

    return { user: data.user, role };
  },
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
});
