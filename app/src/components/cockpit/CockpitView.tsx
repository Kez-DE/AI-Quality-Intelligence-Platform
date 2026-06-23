import { useState } from "react";
import { Shield, X } from "lucide-react";
import { useMe } from "@/lib/api";
import { useCockpitRealtime } from "@/hooks/useCockpitRealtime";
import { useCockpitFilter } from "./CockpitFilterContext";
import { DetailDrawer, type DrawerFilter } from "./DetailDrawer";
import { AdvancedAnalytics } from "./widgets/AdvancedAnalytics";
import { AlertsPanel } from "./widgets/AlertsPanel";
import { CategoryBreakdown } from "./widgets/CategoryBreakdown";
import { DriverWatchlist } from "./widgets/DriverWatchlist";
import { Heatmap } from "./widgets/Heatmap";
import { KpiStrip } from "./widgets/KpiStrip";
import { LiveFeed } from "./widgets/LiveFeed";
import { TeamLeaderboard } from "./widgets/TeamLeaderboard";
import { TicketBoard } from "./widgets/TicketBoard";
import { TrendCard } from "./widgets/TrendCard";

function SecurityNotice() {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-muted/50 p-6 text-center">
      <Shield className="h-6 w-6 text-muted-foreground mx-auto mb-2" />
      <h3 className="text-sm font-semibold text-foreground">Khu vực hạn chế</h3>
      <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
        Một số dữ liệu nội bộ đã được ẩn vì quyền bảo mật của tài khoản Khách.
      </p>
    </div>
  );
}

function UnassignedNotice() {
  return (
    <div className="rounded-2xl border border-dashed border-xanh-amber/50 bg-xanh-amber/5 p-6 text-center">
      <Shield className="h-6 w-6 text-xanh-amber mx-auto mb-2" />
      <h3 className="text-sm font-semibold text-foreground">Chưa được phân công phòng ban</h3>
      <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
        Tài khoản của bạn chưa được gán phòng ban. Liên hệ admin để được cấp quyền xem dữ liệu.
      </p>
    </div>
  );
}

function FilterChip({ filter, clear }: { filter: { topic: string | null; area: string | null }; clear: () => void }) {
  const parts = [filter.topic && `Chủ đề: ${filter.topic}`, filter.area && `Khu vực: ${filter.area}`].filter(Boolean);
  if (parts.length === 0) return null;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="font-mono text-muted-foreground">Đang lọc:</span>
      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-xanh-mint text-xanh-deep border border-xanh-green/40 font-mono">
        {parts.join(" · ")}
        <button onClick={clear} className="ml-1 text-xanh-deep/60 hover:text-xanh-deep">
          <X className="h-3 w-3" />
        </button>
      </span>
    </div>
  );
}

export function CockpitView() {
  const { data: me } = useMe();
  const isGuest = me?.role === "guest";
  const isUnassigned = !!me && me.role !== "admin" && me.role !== "guest" && !me.department;
  const { filter, clear } = useCockpitFilter();
  const [drawer, setDrawer] = useState<DrawerFilter | null>(null);

  useCockpitRealtime();

  if (isUnassigned) {
    return <div className="mt-6"><UnassignedNotice /></div>;
  }

  return (
    <div className="mt-6 space-y-6">
      <FilterChip filter={filter} clear={clear} />
      <KpiStrip />
      <div className="grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-6">
          <TrendCard />
          <CategoryBreakdown
            onOpenDrawer={(topic) =>
              setDrawer({ topic, title: `Phản hồi · ${topic}` })
            }
          />
          {!isGuest ? <LiveFeed /> : <SecurityNotice />}
        </div>
        <aside className="lg:col-span-4 space-y-6">
          {!isGuest && <AlertsPanel />}
          <Heatmap
            onOpenDrawer={(area) =>
              setDrawer({ area, title: `Phản hồi · ${area}` })
            }
          />
          {!isGuest && <TeamLeaderboard />}
          {!isGuest && <DriverWatchlist />}
        </aside>
      </div>
      {!isGuest && <TicketBoard />}

      <AdvancedAnalytics />

      <DetailDrawer filter={drawer} onClose={() => setDrawer(null)} />
    </div>
  );
}
