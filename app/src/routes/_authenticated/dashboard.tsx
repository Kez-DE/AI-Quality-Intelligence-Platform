import { createFileRoute } from "@tanstack/react-router";
import { Gauge } from "lucide-react";
import { CockpitFilterProvider } from "@/components/cockpit/CockpitFilterContext";
import { CockpitView } from "@/components/cockpit/CockpitView";

export const Route = createFileRoute("/_authenticated/dashboard")({
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className="h-10 w-10 rounded-xl grid place-items-center text-white shadow-[var(--shadow-green)]"
            style={{ background: "var(--gradient-green)" }}
          >
            <Gauge className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <h1 className="font-display text-xl font-bold tracking-tight">Bảng điều khiển Chất lượng</h1>
            <p className="text-xs text-muted-foreground font-mono">xanhSM · Quality Operation Cockpit</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-full bg-xanh-mint text-xanh-deep border border-xanh-green/30">
          <span className="h-1.5 w-1.5 rounded-full bg-xanh-green animate-pulse" />
          LIVE · near-real-time
        </span>
      </div>

      <CockpitFilterProvider>
        <CockpitView />
      </CockpitFilterProvider>
    </div>
  );
}
