import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { supabase } from "@/integrations/supabase/client";
import AppShell from "@/components/AppShell";
import { ChangePasswordScreen, PendingAccountScreen } from "@/components/AccountGate";
import { staffWebGate, toRole } from "@/lib/access";

export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: async ({ location }) => {
    // If OAuth returned an error in the hash, pass it to /auth via sessionStorage
    const hash = location.hash?.slice(1) ?? "";
    if (hash) {
      const p = new URLSearchParams(hash);
      const desc = p.get("error_description") || p.get("error");
      if (desc) {
        sessionStorage.setItem("oauth_error", decodeURIComponent(desc.replace(/\+/g, " ")));
        throw redirect({ to: "/auth" });
      }
    }

    const { data: sessionData } = await supabase.auth.getSession();
    if (!sessionData.session) throw redirect({ to: "/auth" });

    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) throw redirect({ to: "/auth" });

    // Fail closed: a failed or empty profile read leaves role unknown → pending.
    let profileRole: unknown = null;
    try {
      const { data: profile } = await supabase
        .from("profiles")
        .select("role")
        .eq("id", data.user.id)
        .maybeSingle();
      profileRole = profile?.role;
    } catch {
      profileRole = null;
    }

    const gate = staffWebGate({
      role: profileRole,
      // app_metadata: only the backend (service role) can set or clear it.
      mustChangePassword: data.user.app_metadata?.must_change_password === true,
      pathname: location.pathname,
    });
    if (gate === "to-dashboard") throw redirect({ to: "/dashboard" });

    return { user: data.user, role: toRole(profileRole), gate };
  },
  component: AuthenticatedLayout,
});

// Only an allowed Staff account gets AppShell (nav, data, chat widget) and the
// child route. The other gates render a standalone screen, so no child route
// mounts and nothing is fetched from the backend.
function AuthenticatedLayout() {
  const { gate, user } = Route.useRouteContext();
  if (gate === "change-password") return <ChangePasswordScreen />;
  if (gate === "pending") return <PendingAccountScreen email={user.email} />;
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
