// Kiểu dữ liệu khớp response của GET /api/cockpit/overview (pipeline/main.py).

export interface CockpitScope {
  team: string | null; // null = toàn bộ (admin) hoặc guest
  role: "admin" | "manager" | "staff" | "guest";
  unassigned: boolean; // ops chưa gán phòng
  restricted: boolean; // guest
}

export interface CockpitKpis {
  feedback_today: number;
  feedback_today_delta_pct: number | null;
  negative_rate: number;
  negative_rate_today: number;
  needs_review: number;
  window_total: number;
  // chỉ ops/admin:
  alerts_open?: number;
  tickets_open?: number;
  tickets_by_priority?: Record<string, number>;
  corrections_7d?: number;
}

export interface TrendPoint {
  date: string;
  total: number;
  negative: number;
}

export interface CategorySlice {
  topic: string;
  count: number;
  pct: number;
}

export interface HeatmapData {
  areas: string[];
  hours: string[];
  cells: { area: string; hour: string; negative_count: number }[];
}

export interface SentimentPoint {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
}

export interface RiskBucket {
  score: number;
  count: number;
}

export interface FunnelData {
  total: number;
  classified: number;
  needs_review: number;
  alerts_triggered: number;
  tickets_created: number;
  resolved: number;
}

export interface SankeyLink {
  from: string;
  to: string;
  value: number;
}

export interface CockpitOverview {
  scope: CockpitScope;
  window_days: number;
  generated_at: string;
  kpis: CockpitKpis;
  trend: TrendPoint[];
  trend_sentiment: SentimentPoint[];
  categories: CategorySlice[];
  heatmap: HeatmapData;
  risk_distribution: RiskBucket[];
  funnel: FunnelData | Record<string, never>;
  sankey_flows: SankeyLink[];
  db_error: string | null;
}
