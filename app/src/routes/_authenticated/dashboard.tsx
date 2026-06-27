import { createFileRoute } from "@tanstack/react-router";
import { Gauge, Sparkles } from "lucide-react";
import { CockpitFilterProvider } from "@/components/cockpit/CockpitFilterContext";
import { CockpitView } from "@/components/cockpit/CockpitView";

export const Route = createFileRoute("/_authenticated/dashboard")({
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <div>
      {/* Hero header — bố cục nổi bật; Cockpit (KPI + widgets) giữ nguyên bên dưới */}
      <section className="relative overflow-hidden rounded-3xl border bg-gradient-to-br from-primary/10 via-card to-card p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-primary/20 blur-3xl" />
        <div className="pointer-events-none absolute -left-12 -bottom-24 h-56 w-56 rounded-full bg-xanh-mint/50 blur-3xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className="h-12 w-12 rounded-2xl grid place-items-center text-white shadow-[var(--shadow-green)] shrink-0"
              style={{ background: "var(--gradient-green)" }}
            >
              <Gauge className="h-6 w-6" />
            </div>
            <div className="leading-tight">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-xanh-deep">
                <Sparkles className="h-3.5 w-3.5" />
                xanhSM · Quality Operation Cockpit
              </span>
              <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight mt-1">
                Bảng điều khiển Chất lượng
              </h1>
              <p className="text-sm text-muted-foreground mt-1.5 max-w-xl">
                Giám sát phản hồi, phát hiện điểm nóng và theo dõi SLA theo thời gian thực.
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-full bg-xanh-mint text-xanh-deep border border-xanh-green/30 shrink-0">
            <span className="h-1.5 w-1.5 rounded-full bg-xanh-green animate-pulse" />
            LIVE · near-real-time
          </span>
        </div>
      </section>

      <CockpitFilterProvider>
        <CockpitView />
      </CockpitFilterProvider>
    </div>
  );
}
