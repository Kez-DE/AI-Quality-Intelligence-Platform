import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2, TrendingUp, AlertCircle, BarChart3, Tag, MessageSquare, AlertTriangle } from "lucide-react";

export const Route = createFileRoute("/_authenticated/department-insights")({
  component: DepartmentInsightsPage,
});

type InsightData = {
  team: string;
  period_hours: number;
  total_feedback: number;
  severity_distribution: Record<string, number>;
  top_topics: Array<{ topic: string; count: number }>;
  recent_samples: Array<{ id: string; text: string; area: string }>;
  analysis?: {
    status: string;
    analysis?: {
      root_cause_summary: string;
      risk_level: string;
      action_items: Array<{ action: string; deadline: string }>;
    };
  };
};

const TEAMS = ["Safety", "IT", "Operations", "Customer Service", "Finance", "Marketing"];
const API_BASE = import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000";

function DepartmentInsightsPage() {
  const [insights, setInsights] = useState<Record<string, InsightData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      
      try {
        // T-C-R: Promise.all to eliminate waterfall loading (Performance optimization)
        const fetchPromises = TEAMS.map(team => 
          fetch(`${API_BASE}/api/insights/departments/${encodeURIComponent(team)}`)
            .then(res => {
              if (!res.ok) throw new Error(`Lỗi tải dữ liệu ${team}`);
              return res.json();
            })
            .then(json => ({ team, data: json.data }))
        );
        
        const results = await Promise.allSettled(fetchPromises);
        
        const newInsights: Record<string, InsightData> = {};
        results.forEach(res => {
          if (res.status === "fulfilled" && res.value.data) {
            newInsights[res.value.team] = res.value.data;
          }
        });
        
        setInsights(newInsights);
      } catch (err) {
        setError("Không thể kết nối đến hệ thống Agent. Vui lòng thử lại sau.");
      } finally {
        setLoading(false);
      }
    }
    
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-2">
            <TrendingUp className="h-7 w-7 text-xanh-green" />
            Department Insights
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Báo cáo nguyên nhân gốc rễ (Root Cause) tổng hợp bởi AI Analyst cho từng phòng ban.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground space-y-4">
          <Loader2 className="h-10 w-10 animate-spin text-xanh-green" />
          <p className="animate-pulse">AI Analyst đang tổng hợp dữ liệu toàn hệ thống...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-2xl flex items-start gap-4">
          <AlertCircle className="h-6 w-6 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold">Lỗi tải dữ liệu</h3>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          {TEAMS.map(team => {
            const data = insights[team];
            if (!data || data.total_feedback === 0) return null;
            
            const ai = data.analysis?.analysis;
            
            return (
              <div key={team} className="rounded-2xl border-2 border-border bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
                {/* Header */}
                <div className="flex items-start justify-between border-b pb-4 mb-4">
                  <div>
                    <h2 className="font-display text-xl font-bold text-xanh-deep">{team}</h2>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs font-mono bg-muted px-2 py-1 rounded-md text-muted-foreground">
                        {data.total_feedback} feedback (24h)
                      </span>
                      {data.severity_distribution.CRITICAL > 0 && (
                        <span className="text-xs font-mono bg-red-100 text-red-700 px-2 py-1 rounded-md flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          {data.severity_distribution.CRITICAL} Critical
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* AI Risk Badge */}
                  {ai && (
                    <div className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider ${
                      ai.risk_level === 'CRITICAL' ? 'bg-red-600 text-white' :
                      ai.risk_level === 'HIGH' ? 'bg-orange-500 text-white' :
                      ai.risk_level === 'MEDIUM' ? 'bg-yellow-400 text-yellow-900' :
                      'bg-green-500 text-white'
                    }`}>
                      Risk: {ai.risk_level}
                    </div>
                  )}
                </div>

                {/* AI Analysis Section */}
                {ai ? (
                  <div className="space-y-4">
                    <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                      <h3 className="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <Brain className="h-3.5 w-3.5 text-xanh-deep" /> Root Cause Summary
                      </h3>
                      <p className="text-sm font-medium leading-relaxed text-slate-800">
                        {ai.root_cause_summary}
                      </p>
                    </div>

                    <div>
                      <h3 className="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <TrendingUp className="h-3.5 w-3.5 text-xanh-green" /> Action Items
                      </h3>
                      <ul className="space-y-2">
                        {ai.action_items.map((item, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm bg-white border border-border rounded-lg p-2.5">
                            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-xanh-mint text-xanh-deep flex items-center justify-center text-[10px] font-bold">
                              {idx + 1}
                            </span>
                            <span className="flex-1">{item.action}</span>
                            <span className="flex-shrink-0 text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                              {item.deadline}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-6 bg-slate-50 rounded-xl border border-dashed">
                    Không có phân tích AI chuyên sâu cho bộ dữ liệu này.
                  </div>
                )}

                {/* Data Snippets */}
                <div className="mt-5 pt-4 border-t grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1">
                      <BarChart3 className="h-3.5 w-3.5" /> Top Topics
                    </h4>
                    <div className="space-y-1.5">
                      {data.top_topics.slice(0, 3).map(t => (
                        <div key={t.topic} className="flex justify-between items-center text-xs">
                          <span className="truncate pr-2">{t.topic}</span>
                          <span className="font-mono text-muted-foreground">{t.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1">
                      <MessageSquare className="h-3.5 w-3.5" /> Sample Quotes
                    </h4>
                    <div className="space-y-1.5">
                      {data.recent_samples.slice(0, 2).map(s => (
                        <div key={s.id} className="text-[11px] leading-tight text-slate-600 line-clamp-2 bg-slate-50 p-1.5 rounded">
                          "{s.text}"
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Thêm icon Brain do thiếu ở import ban đầu
import { Brain } from "lucide-react";
