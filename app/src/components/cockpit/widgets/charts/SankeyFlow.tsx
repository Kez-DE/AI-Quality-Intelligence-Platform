import { useMemo, useState } from "react";
import { GitBranch } from "lucide-react";
import { useCockpitOverview } from "@/hooks/useCockpitOverview";
import type { SankeyLink } from "../../types";
import { Card, SectionHeader } from "../../primitives";

// Màu node theo nhóm
const NODE_COLOR: Record<string, string> = {
  positive: "var(--color-chart-2)",
  neutral: "var(--color-chart-1)",
  negative: "var(--color-chart-3)",
  P1: "var(--color-chart-2)",
  P2: "var(--color-chart-1)",
  P3: "var(--color-chart-4)",
  P4: "var(--color-chart-3)",
  P5: "var(--color-chart-3)",
  open: "var(--color-chart-4)",
  in_progress: "var(--color-chart-1)",
  resolved: "var(--color-chart-2)",
};

const NODE_LABEL: Record<string, string> = {
  positive: "Tích cực", neutral: "Trung tính", negative: "Tiêu cực",
  open: "Đang mở", in_progress: "Đang xử lý", resolved: "Đã xong",
};

const COL_ORDER = [
  ["positive", "neutral", "negative"],
  ["P5", "P4", "P3", "P2", "P1"],
  ["open", "in_progress", "resolved"],
];

const COL_LABEL = ["Sentiment", "Severity", "Trạng thái"];

function buildGraph(flows: SankeyLink[]) {
  const nodeSet = new Set<string>();
  flows.forEach((f) => { nodeSet.add(f.from); nodeSet.add(f.to); });

  // Tổng value mỗi node để tính chiều cao
  const nodeTotals: Record<string, number> = {};
  flows.forEach((f) => {
    nodeTotals[f.from] = (nodeTotals[f.from] ?? 0) + f.value;
    nodeTotals[f.to] = (nodeTotals[f.to] ?? 0) + f.value;
  });

  const maxVal = Math.max(...Object.values(nodeTotals), 1);
  return { nodeSet, nodeTotals, maxVal };
}

const SVG_W = 560;
const SVG_H = 300;
const COL_X = [40, 220, 400];
const NODE_W = 14;
const COL_WIDTH = 120;

function SankeyCanvas({ flows }: { flows: SankeyLink[] }) {
  const [hoveredLink, setHoveredLink] = useState<SankeyLink | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  const { nodeTotals, maxVal } = useMemo(() => buildGraph(flows), [flows]);

  // Tính vị trí Y cho từng node trong mỗi cột
  const colNodes = useMemo(() => {
    return COL_ORDER.map((col) =>
      col.filter((n) => (nodeTotals[n] ?? 0) > 0)
    );
  }, [nodeTotals]);

  const nodeY: Record<string, { top: number; height: number }> = useMemo(() => {
    const result: Record<string, { top: number; height: number }> = {};
    colNodes.forEach((nodes, ci) => {
      const totalHeight = SVG_H - 40;
      const gap = nodes.length > 1 ? 8 : 0;
      const usable = totalHeight - gap * (nodes.length - 1);
      let y = 20;
      nodes.forEach((n) => {
        const h = Math.max(12, Math.round((nodeTotals[n] / maxVal) * usable));
        result[n] = { top: y, height: h };
        y += h + gap;
      });
      void ci;
    });
    return result;
  }, [colNodes, nodeTotals, maxVal]);

  // Map node → column index
  const nodeCol: Record<string, number> = {};
  COL_ORDER.forEach((col, ci) => col.forEach((n) => { nodeCol[n] = ci; }));

  // Offset tracking để link không chồng lên nhau
  const fromOffset: Record<string, number> = {};
  const toOffset: Record<string, number> = {};

  const links = flows
    .filter((f) => f.value > 0 && nodeY[f.from] && nodeY[f.to])
    .map((f) => {
      const fromNode = nodeY[f.from];
      const toNode = nodeY[f.to];
      const ratio = f.value / maxVal;
      const lh = Math.max(2, Math.round(ratio * (Math.min(fromNode.height, toNode.height))));

      const fromOff = fromOffset[f.from] ?? 0;
      fromOffset[f.from] = fromOff + lh;
      const toOff = toOffset[f.to] ?? 0;
      toOffset[f.to] = toOff + lh;

      const fromColIdx = nodeCol[f.from] ?? 0;
      const toColIdx = nodeCol[f.to] ?? 1;
      const x0 = COL_X[fromColIdx] + NODE_W;
      const y0 = fromNode.top + fromOff + lh / 2;
      const x1 = COL_X[toColIdx];
      const y1 = toNode.top + toOff + lh / 2;
      const mx = (x0 + x1) / 2;

      return { f, x0, y0, x1, y1, mx, lh, color: NODE_COLOR[f.from] ?? "var(--color-muted-foreground)" };
    });

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="w-full"
        style={{ height: SVG_H }}
        onMouseLeave={() => { setHoveredLink(null); setTooltip(null); }}
      >
        {/* Column labels */}
        {COL_LABEL.map((label, ci) => (
          <text
            key={label}
            x={COL_X[ci] + NODE_W / 2}
            y={10}
            textAnchor="middle"
            fontSize={9}
            fontFamily="JetBrains Mono"
            fill="var(--color-muted-foreground)"
          >
            {label}
          </text>
        ))}

        {/* Links */}
        {links.map(({ f, x0, y0, x1, y1, mx, lh, color }) => {
          const isHov = hoveredLink === f;
          return (
            <path
              key={`${f.from}-${f.to}`}
              d={`M ${x0},${y0 - lh / 2} C ${mx},${y0 - lh / 2} ${mx},${y1 - lh / 2} ${x1},${y1 - lh / 2} L ${x1},${y1 + lh / 2} C ${mx},${y1 + lh / 2} ${mx},${y0 + lh / 2} ${x0},${y0 + lh / 2} Z`}
              fill={color}
              opacity={isHov ? 0.65 : 0.3}
              className="transition-opacity cursor-pointer"
              onMouseEnter={(e) => {
                setHoveredLink(f);
                const rect = (e.currentTarget.closest("svg") as SVGSVGElement).getBoundingClientRect();
                setTooltip({
                  x: e.clientX - rect.left,
                  y: e.clientY - rect.top - 36,
                  text: `${NODE_LABEL[f.from] ?? f.from} → ${NODE_LABEL[f.to] ?? f.to}: ${f.value}`,
                });
              }}
            />
          );
        })}

        {/* Nodes */}
        {Object.entries(nodeY).map(([name, { top, height }]) => {
          const ci = nodeCol[name] ?? 0;
          const x = COL_X[ci];
          const color = NODE_COLOR[name] ?? "var(--color-chart-1)";
          const label = NODE_LABEL[name] ?? name;
          const isRight = ci === 2;
          return (
            <g key={name}>
              <rect x={x} y={top} width={NODE_W} height={height} fill={color} rx={3} />
              <text
                x={isRight ? x + NODE_W + 6 : x - 6}
                y={top + height / 2 + 4}
                textAnchor={isRight ? "start" : "end"}
                fontSize={10}
                fontFamily="JetBrains Mono"
                fill="var(--color-foreground)"
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[11px] font-mono shadow-md whitespace-nowrap"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}

export function SankeyFlow() {
  const { data: ov, isLoading } = useCockpitOverview();
  const flows = ov?.sankey_flows ?? [];

  return (
    <Card>
      <SectionHeader
        icon={GitBranch}
        title="Luồng: Sentiment → Severity → Trạng thái"
        subtitle="Hover vào link để xem số lượng phản hồi qua từng bước"
      />
      <div className="px-4 pb-4 pt-2">
        {isLoading ? (
          <div className="h-72 animate-pulse bg-muted/40 rounded-xl" />
        ) : flows.length === 0 ? (
          <div className="h-72 flex flex-col items-center justify-center text-xs text-muted-foreground gap-2">
            <GitBranch className="h-7 w-7 opacity-30" />
            <span>Chưa có dữ liệu luồng</span>
          </div>
        ) : (
          <SankeyCanvas flows={flows} />
        )}
      </div>
    </Card>
  );
}
