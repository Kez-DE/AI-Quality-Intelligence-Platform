import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import {
  Loader2,
  FileText,
  Calendar,
  Building2,
  CheckCircle2,
  ClipboardCopy,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { ALL_TEAMS, useMe, apiFetch, isUnassignedOps } from "@/lib/api";
import { NoDepartmentNotice } from "@/components/NoDepartmentNotice";
import { MarkdownContent } from "@/components/MarkdownContent";

export const Route = createFileRoute("/_authenticated/reports")({
  component: ReportsPage,
});

type Report = {
  id: string;
  team: string;
  report_date: string;
  content: string;
  created_at: string;
  approved: boolean;
  approved_by: string | null;
  approved_at: string | null;
};

function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<string>("All");
  const { data: me } = useMe();
  const isManager = me?.role === "admin" || me?.role === "manager";
  const isAdmin = me?.role === "admin";

  const loadData = useCallback(
    async (team?: string) => {
      if (!isManager) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const path = team && team !== "All" ? `/api/reports?team=${team}` : "/api/reports";
        const json = await apiFetch<{ data: Report[] }>(path);
        setReports(json.data || []);
      } catch {
        toast.error("Không thể tải danh sách báo cáo.");
      } finally {
        setLoading(false);
      }
    },
    [isManager],
  );

  useEffect(() => {
    if (me?.role && isManager) void loadData(selectedTeam);
  }, [isManager, loadData, me?.role, selectedTeam]);

  if (!isManager) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Chỉ Trưởng phòng hoặc Admin mới xem được trang Báo Cáo.
      </div>
    );
  }

  if (isUnassignedOps(me)) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <FileText className="h-8 w-8 text-xanh-deep" />
          Báo cáo Tự động (AI)
        </h1>
        <NoDepartmentNotice />
      </div>
    );
  }

  async function handleApprove(reportId: string) {
    try {
      await apiFetch(`/api/reports/${reportId}/approve`, { method: "PATCH" });
      setReports((prev) =>
        prev.map((r) =>
          r.id === reportId
            ? {
                ...r,
                approved: true,
                approved_by: me?.email ?? null,
                approved_at: new Date().toISOString(),
              }
            : r,
        ),
      );
      toast.success("Đã duyệt báo cáo thành công.");
    } catch {
      toast.error("Không thể duyệt báo cáo.");
    }
  }

  async function handleCopyMarkdown(content: string) {
    try {
      await navigator.clipboard.writeText(content);
      toast.success("Đã copy Markdown");
    } catch {
      toast.error("Không thể copy nội dung.");
    }
  }

  async function handleGenerateReport() {
    const team = isAdmin ? selectedTeam : me?.department;
    if (!team || team === "All") {
      toast.error("Vui lòng chọn một phòng ban cụ thể.");
      return;
    }
    setGenerating(true);
    try {
      const json = await apiFetch<{
        data: { status: string; stored?: boolean; reason?: string };
      }>(`/api/agent/generate-report?team=${encodeURIComponent(team)}`, { method: "POST" });
      if (json.data.reason === "approved_report_locked") {
        toast.error("Báo cáo hôm nay đã được duyệt nên không thể ghi đè.");
      } else if (json.data.status === "skipped") {
        toast.error("Phòng ban chưa có feedback để tạo báo cáo.");
      } else {
        toast.success("Đã tạo báo cáo mới nhất.");
      }
      await loadData(selectedTeam);
    } catch {
      toast.error("Không thể tạo báo cáo mới.");
    } finally {
      setGenerating(false);
    }
  }

  const teams = ["All", ...ALL_TEAMS];
  return (
    <div className="mx-auto max-w-6xl space-y-6 animate-in fade-in slide-in-from-bottom-2">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-2">
            <FileText className="h-8 w-8 text-xanh-deep" />
            Báo cáo Tự động (AI)
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Tổng hợp tình hình vận hành, các vấn đề nóng và cảnh báo SLA rủi ro mỗi ngày.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isAdmin ? (
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <select
                className="border-border bg-card text-sm rounded-lg py-2 px-3 focus:outline-none focus:ring-2 focus:ring-xanh-green/50"
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
              >
                {teams.map((t) => (
                  <option key={t} value={t}>
                    {t === "All" ? "Tất cả phòng ban" : `Phòng ${t}`}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            me?.department && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Building2 className="h-4 w-4" />
                Phòng {me.department}
              </div>
            )
          )}
          <button
            type="button"
            onClick={handleGenerateReport}
            disabled={generating || (isAdmin && selectedTeam === "All")}
            title={
              isAdmin && selectedTeam === "All"
                ? "Chọn một phòng ban để tạo báo cáo"
                : "Tạo báo cáo mới nhất"
            }
            className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-xanh-deep px-4 text-sm font-semibold text-white transition-colors hover:bg-xanh-deep/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Tạo báo cáo mới
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
        </div>
      ) : reports.length === 0 ? (
        <div className="border border-border bg-card p-12 text-center text-muted-foreground shadow-sm rounded-lg">
          Chưa có báo cáo nào được sinh ra cho phòng ban này.
        </div>
      ) : (
        <div className="space-y-6">
          {reports.map((report) => {
            const team = report.team || "Unknown";
            const content = report.content || "";
            const hasCritical = content.includes("**CRITICAL**");
            const hasWarning = content.includes("**WARNING**") || content.includes("**HIGH**");

            return (
              <div
                key={report.id}
                className={`overflow-hidden rounded-lg border bg-card shadow-[var(--shadow-card)] ${hasCritical ? "border-red-500/50 shadow-red-500/10" : hasWarning ? "border-amber-500/50 shadow-amber-500/10" : "border-border"}`}
              >
                <div
                  className={`flex flex-wrap items-center justify-between gap-3 border-b border-border p-5 ${hasCritical ? "bg-red-50" : hasWarning ? "bg-amber-50" : "bg-muted/5"}`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-10 w-10 rounded-full flex items-center justify-center font-bold font-mono text-xs ${hasCritical ? "bg-red-100 text-red-700" : hasWarning ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}
                    >
                      {team.substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <h3
                        className={`font-bold ${hasCritical ? "text-red-900" : hasWarning ? "text-amber-900" : "text-xanh-deep"}`}
                      >
                        Báo cáo Vận hành - Phòng {team}
                      </h3>
                      <p
                        className={`text-xs flex items-center gap-1 mt-0.5 ${hasCritical ? "text-red-700" : hasWarning ? "text-amber-700" : "text-muted-foreground"}`}
                      >
                        <Calendar className="h-3 w-3" />{" "}
                        {new Date(report.report_date).toLocaleDateString("vi-VN")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!report.approved && (
                      <button
                        type="button"
                        onClick={() => handleApprove(report.id)}
                        title="Duyệt báo cáo"
                        aria-label="Duyệt báo cáo"
                        className="grid h-8 w-8 place-items-center rounded-md border border-green-200 bg-green-50 text-green-700 transition-colors hover:bg-green-100"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                      </button>
                    )}
                    {report.approved ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-green-700 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Đã duyệt
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-100 text-yellow-700">
                        Chờ duyệt
                      </span>
                    )}
                    {hasCritical && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700">
                        🚨 CRITICAL
                      </span>
                    )}
                    {hasWarning && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700">
                        ⚠️ WARNING
                      </span>
                    )}
                    <span className="text-[10px] text-muted-foreground font-mono bg-muted px-2 py-1 rounded">
                      AI Generated
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopyMarkdown(content)}
                      title="Sao chép báo cáo Markdown"
                      aria-label="Sao chép báo cáo Markdown"
                      className="grid h-8 w-8 place-items-center rounded-md border border-border bg-card text-muted-foreground transition-colors hover:text-foreground"
                    >
                      <ClipboardCopy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="p-5 sm:p-7">
                  <MarkdownContent>{content}</MarkdownContent>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
