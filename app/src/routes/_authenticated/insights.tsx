import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2, Building2, AlertCircle, Sparkles, RefreshCw, BarChart3, MessageSquare, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { apiFetch, useMe, visibleTeams, isUnassignedOps } from "@/lib/api";
import { NoDepartmentNotice } from "@/components/NoDepartmentNotice";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { topicLabel } from "@/lib/labels";
import { regionLabel } from "@/lib/regions";

export const Route = createFileRoute("/_authenticated/insights")({
  component: InsightsPage,
});

const TEAM_LABEL: Record<string, string> = {
  IT: "Kỹ thuật / IT",
  CSKH: "Chăm sóc khách hàng",
  "Vận hành": "Vận hành",
  Marketing: "Marketing",
};

const TEAM_HINT: Record<string, string> = {
  IT: "Lỗi ứng dụng, bản đồ, thanh toán trong app",
  CSKH: "Khiếu nại chung, trải nghiệm dịch vụ, giá cước, voucher, cần phản hồi khách",
  "Vận hành": "Tài xế, thiếu cuốc, chậm trễ, khu vực nóng, sự cố an toàn hiện trường",
  Marketing: "Nhận diện thương hiệu, cảm nhận tích cực/tiêu cực thị trường",
};

const RISK_LABEL: Record<string, string> = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Nghiêm trọng",
};

const SEVERITY_LABEL: Record<string, string> = {
  CRITICAL: "Nghiêm trọng",
  WARNING: "Cảnh báo",
  WATCH: "Theo dõi",
  INFO: "Thông tin",
};

type ActionItem = { action: string; deadline?: string | null };

type Analysis = {
  status?: string;
  reason?: string;
  analysis?: {
    root_cause_summary?: string;
    risk_level?: string;
    action_items?: ActionItem[];
  } | null;
};

type Department = {
  team: string;
  period_hours?: number;
  total_feedback: number;
  severity_distribution?: Record<string, number>;
  top_topics?: { topic: string; count: number }[];
  recent_samples?: { id?: string; text?: string; area?: string | null }[];
  analysis?: Analysis;
  error?: string;
};

type ApiResponse<T> = { status: string; data: T };

function severityNum(s: string | null) {
  if (!s) return 0;
  if (s.includes("P5")) return 5;
  if (s.includes("P4")) return 4;
  if (s.includes("P3")) return 3;
  if (s.includes("P2")) return 2;
  if (s.includes("P1")) return 1;
  return 0;
}

function InsightsPage() {
  const { data: me, isLoading: meLoading } = useMe();
  const teams = visibleTeams(me);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [analyzingTeam, setAnalyzingTeam] = useState<string | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<string | null>(null);
  const [showCriticalModal, setShowCriticalModal] = useState(false);

  async function loadMetrics() {
    if (teams.length === 0) return;
    setLoadingMetrics(true);
    try {
      // Load nhanh: KHÔNG gọi LLM. Mỗi team dùng Insight Agent để gom số liệu.
      const results = await Promise.allSettled(
        teams.map((team) =>
          apiFetch<ApiResponse<Department>>(
            `/api/insights/departments/${encodeURIComponent(team)}?hours=720&with_analysis=false`,
          ).then((json) => json.data),
        ),
      );

      const rows = results.map((res, idx) => {
        const team = teams[idx];
        if (res.status === "fulfilled") return res.value;
        return {
          team,
          total_feedback: 0,
          severity_distribution: { CRITICAL: 0, WARNING: 0, WATCH: 0, INFO: 0 },
          top_topics: [],
          recent_samples: [],
          error: res.reason instanceof Error ? res.reason.message : "Không tải được dữ liệu",
        } satisfies Department;
      });

      setDepartments(rows);
      setLastLoadedAt(new Date().toLocaleTimeString("vi-VN"));
      toast.success(
        teams.length === 1 ? `Đã tải số liệu phòng ${teams[0]}` : `Đã tải số liệu ${teams.length} phòng ban`,
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không tải được phân tích phòng ban");
    } finally {
      setLoadingMetrics(false);
    }
  }

  async function analyzeTeam(team: string) {
    setAnalyzingTeam(team);
    try {
      // Gọi Analyst Agent + LLM chỉ cho team người dùng chọn → tiết kiệm credit, phản hồi nhanh hơn.
      const json = await apiFetch<ApiResponse<Department>>(
        `/api/insights/departments/${encodeURIComponent(team)}?hours=720&with_analysis=true`,
      );
      setDepartments((prev) => prev.map((d) => (d.team === team ? json.data : d)));
      toast.success(`Đã phân tích sâu: ${TEAM_LABEL[team] ?? team}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không chạy được Analyst Agent");
    } finally {
      setAnalyzingTeam(null);
    }
  }

  useEffect(() => {
    if (me && teams.length > 0) void loadMetrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id]);

  const totalFeedback = departments.reduce((sum, d) => sum + (d.total_feedback || 0), 0);
  const teamsWithData = departments.filter((d) => d.total_feedback > 0).length;
  const criticalCount = departments.reduce((sum, d) => sum + (d.severity_distribution?.CRITICAL ?? 0), 0);

  if (!meLoading && isUnassignedOps(me)) {
    return (
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Building2 className="h-6 w-6 text-xanh-green" />
          Phân tích phòng ban
        </h1>
        <NoDepartmentNotice />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-2">
            <Building2 className="h-6 w-6 text-xanh-green" />
            Phân tích phòng ban
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            Trang này biến 6 agent thành tính năng thật: Insight Agent gom số liệu nhanh theo phòng ban,
            Router Agent giải thích vì sao phản hồi đi về team đó, Analyst Agent chỉ gọi LLM khi cần phân tích sâu.
          </p>
        </div>
        <button
          onClick={loadMetrics}
          disabled={loadingMetrics}
          className="h-11 px-5 rounded-xl text-white font-semibold flex items-center gap-2 shadow-[var(--shadow-green)] disabled:opacity-60"
          style={{ background: "var(--gradient-green)" }}
        >
          {loadingMetrics ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          {loadingMetrics ? "Đang tải..." : "Tải lại số liệu"}
        </button>
      </div>

      <div className="grid sm:grid-cols-3 gap-3">
        <SummaryCard label="Tổng phản hồi" value={totalFeedback} icon={MessageSquare} />
        <SummaryCard label="Phòng ban có dữ liệu" value={`${teamsWithData}/${teams.length}`} icon={Building2} />
        <SummaryCard 
          label="Ca nghiêm trọng" 
          value={criticalCount} 
          icon={ShieldCheck} 
          tone="coral" 
          onClick={() => setShowCriticalModal(true)} 
        />
      </div>

      <CriticalCasesModal 
        open={showCriticalModal} 
        onOpenChange={setShowCriticalModal} 
      />

      <div className="rounded-2xl border border-border bg-card p-4 text-sm text-muted-foreground">
        <div className="font-semibold text-foreground mb-1">Cách hoạt động</div>
        <ol className="list-decimal ml-5 space-y-1">
          <li>Feedback đã được classifier + rule engine gán topic/sentiment/severity.</li>
          <li>Router Agent route từng feedback về đúng phòng ban theo topic + P5 override (về Vận hành).</li>
          <li>Insight Agent tổng hợp số lượng, mức độ, top chủ đề, ví dụ phản hồi.</li>
          <li>Bấm “Phân tích sâu bằng AI” để Analyst Agent gọi LLM cho riêng phòng ban đó.</li>
        </ol>
        {lastLoadedAt && <div className="mt-2 text-xs font-mono">Cập nhật lúc {lastLoadedAt}</div>}
      </div>

      {loadingMetrics && departments.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-10 text-center shadow-[var(--shadow-card)]">
          <Loader2 className="h-6 w-6 animate-spin inline text-xanh-green" />
          <p className="text-sm text-muted-foreground mt-3">Đang gom metric từ phòng ban...</p>
        </div>
      ) : (
        <div className="grid xl:grid-cols-2 gap-4 items-start">
          {departments.map((d) => (
            <DepartmentCard
              key={d.team}
              dept={d}
              analyzing={analyzingTeam === d.team}
              onAnalyze={() => analyzeTeam(d.team)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon: Icon,
  tone = "green",
  onClick,
}: {
  label: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: "green" | "coral";
  onClick?: () => void;
}) {
  return (
    <div 
      onClick={onClick}
      className={`rounded-2xl border border-border bg-card p-4 shadow-[var(--shadow-card)] flex items-center gap-3 ${onClick ? 'cursor-pointer hover:border-xanh-coral/50 transition-colors' : ''}`}
    >
      <div className={`h-10 w-10 rounded-xl grid place-items-center ${tone === "coral" ? "bg-xanh-coral/10 text-xanh-coral" : "bg-xanh-mint text-xanh-deep"}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="font-display text-2xl font-bold">{value}</div>
      </div>
    </div>
  );
}

function CriticalCasesModal({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      apiFetch<{ status: string; data: any[] }>("/api/feedback/recent?limit=500")
        .then((res) => {
          const critical = res.data.filter((f) => severityNum(f.severity) >= 4);
          setCases(critical);
        })
        .finally(() => setLoading(false));
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Các ca nghiêm trọng (P4 / P5)</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="p-10 flex justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-xanh-green" />
          </div>
        ) : cases.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground">Không tìm thấy ca nghiêm trọng nào gần đây.</div>
        ) : (
          <div className="space-y-3 mt-4">
            {cases.map((f) => (
              <div key={f.id} className="rounded-xl border border-xanh-coral/30 bg-xanh-coral/5 p-4">
                <div className="flex justify-between items-start mb-2 gap-4">
                  <div className="font-semibold text-xanh-coral leading-tight">{f.topic || "Không rõ chủ đề"}</div>
                  <div className="text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(f.created_at).toLocaleString("vi-VN")}
                  </div>
                </div>
                <p className="text-sm text-foreground/90 leading-relaxed">{f.text}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-mono">
                  <span className="bg-card/80 px-2 py-1 rounded border">Team: {f.team || "Chưa phân"}</span>
                  <span className="bg-card/80 px-2 py-1 rounded border">Mức độ: {f.severity}</span>
                  {f.area && <span className="bg-card/80 px-2 py-1 rounded border">Khu vực: {regionLabel(f.area)}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function DepartmentCard({
  dept,
  analyzing,
  onAnalyze,
}: {
  dept: Department;
  analyzing: boolean;
  onAnalyze: () => void;
}) {
  const inner = dept.analysis?.analysis ?? null;
  const risk = inner?.risk_level;
  const riskTone =
    risk === "CRITICAL"
      ? "bg-xanh-coral/15 text-xanh-coral border-xanh-coral/30"
      : risk === "HIGH"
        ? "bg-amber-100 text-amber-800 border-amber-300"
        : "bg-xanh-mint text-xanh-deep border-xanh-green/30";
  const severity = dept.severity_distribution ?? {};

  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)] space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display font-semibold flex items-center gap-2">
            <Building2 className="h-4 w-4 text-xanh-deep" />
            {TEAM_LABEL[dept.team] ?? dept.team}
          </h2>
          <p className="text-xs text-muted-foreground mt-1">{TEAM_HINT[dept.team] ?? "Phân tích theo phòng ban"}</p>
        </div>
        <span className="text-xs font-mono text-muted-foreground whitespace-nowrap">
          {dept.total_feedback} phản hồi
        </span>
      </div>

      {dept.error && (
        <div className="rounded-xl border border-xanh-coral/30 bg-xanh-coral/10 p-3 text-sm text-xanh-coral flex gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {dept.error}
        </div>
      )}

      <div className="grid grid-cols-4 gap-2">
        {(["CRITICAL", "WARNING", "WATCH", "INFO"] as const).map((level) => (
          <div key={level} className="rounded-xl bg-muted/50 p-2 text-center">
            <div className="text-[10px] text-muted-foreground">{SEVERITY_LABEL[level]}</div>
            <div className="font-mono font-bold">{severity[level] ?? 0}</div>
          </div>
        ))}
      </div>

      {dept.top_topics && dept.top_topics.length > 0 ? (
        <div>
          <div className="text-[11px] font-mono text-muted-foreground uppercase mb-2 flex items-center gap-1">
            <BarChart3 className="h-3 w-3" /> Chủ đề nổi bật
          </div>
          <div className="flex flex-wrap gap-1.5">
            {dept.top_topics.slice(0, 5).map((t) => (
              <span key={t.topic} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {topicLabel(t.topic)} · {t.count}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Chưa có phản hồi thuộc phòng ban này trong kỳ.</p>
      )}

      {dept.recent_samples && dept.recent_samples.length > 0 && (
        <div>
          <div className="text-[11px] font-mono text-muted-foreground uppercase mb-2">Ví dụ gần nhất</div>
          <div className="space-y-2">
            {dept.recent_samples.slice(0, 2).map((s, idx) => (
              <div key={s.id ?? idx} className="rounded-xl bg-slate-50 border border-slate-100 p-2 text-xs leading-relaxed">
                “{s.text}”
                {s.area && <span className="block mt-1 text-[10px] font-mono text-muted-foreground">{regionLabel(s.area)}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="pt-2 border-t border-border flex flex-wrap items-center justify-between gap-2">
        {risk ? (
          <span className={`inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded border ${riskTone}`}>
            <AlertCircle className="h-3 w-3" />
            Rủi ro: {RISK_LABEL[risk] ?? risk}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">Chưa chạy phân tích sâu bằng LLM.</span>
        )}
        <button
          onClick={onAnalyze}
          disabled={analyzing || dept.total_feedback === 0}
          className="h-9 px-3 rounded-lg border border-xanh-green/40 text-xanh-deep bg-xanh-mint hover:bg-xanh-green/20 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
        >
          {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {analyzing ? "Đang phân tích..." : inner ? "Phân tích lại" : "Phân tích sâu bằng AI"}
        </button>
      </div>

      {inner?.root_cause_summary && (
        <div className="rounded-xl bg-xanh-mint/60 border border-xanh-green/20 p-3">
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
                  {act.deadline && <span className="text-[10px] font-mono text-muted-foreground ml-1">({act.deadline})</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
