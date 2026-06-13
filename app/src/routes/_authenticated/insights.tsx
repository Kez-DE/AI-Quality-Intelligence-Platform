import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Loader2, Building2, AlertCircle, Sparkles } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/insights")({
  component: InsightsPage,
});

const API_BASE = import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000";

// Nhãn phòng ban tiếng Việt (khớp team trong orchestrator).
const TEAM_LABEL: Record<string, string> = {
  IT: "Kỹ thuật / IT",
  Safety: "An toàn",
  CSKH: "Chăm sóc khách hàng",
  "Vận hành": "Vận hành",
  Pricing: "Giá cước",
  Marketing: "Marketing",
};

// Nhãn mức rủi ro tiếng Việt (analyst trả LOW/MEDIUM/HIGH/CRITICAL).
const RISK_LABEL: Record<string, string> = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Nghiêm trọng",
};

type ActionItem = { action: string; deadline?: string };

// analyst_agent trả: { status, analysis: { root_cause_summary, risk_level, action_items[] } }
type Analysis = {
  status?: string;
  analysis?: {
    root_cause_summary?: string;
    risk_level?: string;
    action_items?: ActionItem[];
  } | null;
};

// insight_agent trả: { team, total_feedback, severity_distribution, top_topics[], analysis? }
type Department = {
  team: string;
  total_feedback: number;
  severity_distribution?: Record<string, number>;
  top_topics?: { topic: string; count: number }[];
  analysis?: Analysis;
};

function InsightsPage() {
  // orchestrator trả data dạng object { [team]: Department } -> chuyển thành mảng.
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(false);
  const [ran, setRan] = useState(false);

  async function authToken(): Promise<string | null> {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }

  async function runPipeline() {
    setLoading(true);
    const token = await authToken();
    if (!token) {
      toast.error("Chưa đăng nhập");
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/insights/departments?hours=720`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status}: ${detail.slice(0, 200)}`);
      }
      // shape: { status, data: { departments_processed, data: { IT: {...}, Safety: {...} } } }
      const json = (await res.json()) as {
        data?: { data?: Record<string, Department> };
      };
      const deptMap = json.data?.data ?? {};
      setDepartments(Object.values(deptMap));
      setRan(true);
      toast.success("Đã chạy phân tích đa tác tử");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không chạy được phân tích");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-2">
            <Building2 className="h-6 w-6 text-xanh-green" />
            Phân tích phòng ban
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Hệ đa tác tử (multi-agent) gom phản hồi theo từng phòng ban, định tuyến,
            rồi dùng AI phân tích nguyên nhân gốc và đề xuất hành động.
          </p>
        </div>
        <button
          onClick={runPipeline}
          disabled={loading}
          className="h-11 px-5 rounded-xl text-white font-semibold flex items-center gap-2 shadow-[var(--shadow-green)] disabled:opacity-60"
          style={{ background: "var(--gradient-green)" }}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {loading ? "Đang chạy agent (~1-2 phút)..." : ran ? "Chạy lại" : "Chạy phân tích"}
        </button>
      </div>

      {loading && (
        <div className="rounded-2xl border border-border bg-white p-10 text-center shadow-[var(--shadow-card)]">
          <Loader2 className="h-6 w-6 animate-spin inline text-xanh-green" />
          <p className="text-sm text-muted-foreground mt-3">
            6 tác tử đang phân tích từng phòng ban bằng LLM thật. Việc này mất khoảng 1-2 phút.
          </p>
        </div>
      )}

      {!loading && !ran && (
        <div className="rounded-2xl border border-dashed border-border bg-muted/30 p-10 text-center">
          <Building2 className="h-8 w-8 inline text-muted-foreground" />
          <p className="text-sm text-muted-foreground mt-3">
            Bấm "Chạy phân tích" để hệ đa tác tử tổng hợp tình hình theo phòng ban.
          </p>
        </div>
      )}

      {!loading && ran && (
        <div className="grid md:grid-cols-2 gap-4 items-start">
          {departments.map((d) => (
            <DepartmentCard key={d.team} dept={d} />
          ))}
        </div>
      )}
    </div>
  );
}

function DepartmentCard({ dept }: { dept: Department }) {
  const inner = dept.analysis?.analysis ?? null;
  const risk = inner?.risk_level;
  const riskTone =
    risk === "CRITICAL"
      ? "bg-xanh-coral/15 text-xanh-coral border-xanh-coral/30"
      : risk === "HIGH"
        ? "bg-amber-100 text-amber-800 border-amber-300"
        : "bg-xanh-mint text-xanh-deep border-xanh-green/30";

  return (
    <section className="rounded-2xl border border-border bg-white p-5 shadow-[var(--shadow-card)] space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-display font-semibold flex items-center gap-2">
          <Building2 className="h-4 w-4 text-xanh-deep" />
          {TEAM_LABEL[dept.team] ?? dept.team}
        </h2>
        <span className="text-xs font-mono text-muted-foreground">
          {dept.total_feedback} phản hồi
        </span>
      </div>

      {dept.total_feedback === 0 ? (
        <p className="text-sm text-muted-foreground">Không có phản hồi trong kỳ.</p>
      ) : (
        <>
          {risk && (
            <span className={`inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded border ${riskTone}`}>
              <AlertCircle className="h-3 w-3" />
              Rủi ro: {RISK_LABEL[risk] ?? risk}
            </span>
          )}

          {dept.top_topics && dept.top_topics.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {dept.top_topics.slice(0, 4).map((t) => (
                <span key={t.topic} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                  {t.topic} · {t.count}
                </span>
              ))}
            </div>
          )}

          {inner?.root_cause_summary && (
            <div>
              <div className="text-[11px] font-mono text-muted-foreground uppercase mb-1">Nguyên nhân gốc</div>
              <p className="text-sm">{inner.root_cause_summary}</p>
            </div>
          )}

          {inner?.action_items && inner.action_items.length > 0 && (
            <div>
              <div className="text-[11px] font-mono text-muted-foreground uppercase mb-1">Hành động đề xuất</div>
              <ul className="text-sm space-y-1">
                {inner.action_items.map((act, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-xanh-green mt-0.5">•</span>
                    <span>
                      {act.action}
                      {act.deadline && (
                        <span className="text-[10px] font-mono text-muted-foreground ml-1">({act.deadline})</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
