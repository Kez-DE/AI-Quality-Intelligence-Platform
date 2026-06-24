import { useState } from "react";
import { ChevronDown, ChevronRight, BarChart2 } from "lucide-react";
import { useMe } from "@/lib/api";
import { SentimentLineChart } from "./charts/SentimentLineChart";
import { RiskHistogram } from "./charts/RiskHistogram";
import { PipelineFunnel } from "./charts/PipelineFunnel";
import { SankeyFlow } from "./charts/SankeyFlow";

export function AdvancedAnalytics() {
  const [isOpen, setIsOpen] = useState(false);
  const { data: me } = useMe();

  // Unassigned ops không thấy section này
  const isUnassigned = !!me && me.role !== "admin" && me.role !== "guest" && !me.department;
  if (isUnassigned) return null;

  return (
    <div className="rounded-2xl border border-border bg-card/60 backdrop-blur overflow-hidden">
      {/* Header toggle */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-xanh-mint/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-xanh-mint grid place-items-center flex-shrink-0">
            <BarChart2 className="h-4 w-4 text-xanh-deep" />
          </div>
          <div className="text-left">
            <div className="font-display font-semibold text-sm text-foreground">Phân tích nâng cao</div>
            <div className="text-xs text-muted-foreground mt-0.5">
              Line Chart · Histogram · Funnel · Sankey — 4 biểu đồ
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-xanh-deep bg-xanh-mint px-2 py-0.5 rounded-full border border-xanh-green/30">
            {isOpen ? "Thu gọn" : "Mở rộng"}
          </span>
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Content — lazy mount khi mở */}
      {isOpen && (
        <div className="border-t border-border/60 p-4 space-y-4">
          {/* Line Chart — full width */}
          <SentimentLineChart />

          {/* Histogram + Funnel — 2 cột */}
          <div className="grid lg:grid-cols-12 gap-4">
            <div className="lg:col-span-7">
              <RiskHistogram />
            </div>
            <div className="lg:col-span-5">
              <PipelineFunnel />
            </div>
          </div>

          {/* Sankey — full width */}
          <SankeyFlow />
        </div>
      )}
    </div>
  );
}
