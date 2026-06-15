import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { supabase } from "@/integrations/supabase/client";
import AppShell from "@/components/AppShell";

export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: async ({ location }) => {
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) throw redirect({ to: "/auth" });
    
    // Fetch user role
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', data.user.id)
      .single();
      
    const role = profile?.role || "guest";

    // Route Guard for Guests
    const restrictedForGuests = ["/alerts", "/insights", "/admin"];
    if (role === "guest" && restrictedForGuests.some(p => location.pathname.startsWith(p))) {
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
