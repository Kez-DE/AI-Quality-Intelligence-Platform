import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Loader2,
  FileText,
  Calendar,
  Building2,
  CheckCircle2,
  ClipboardCopy,
  ShieldCheck,
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
  const [selectedTeam, setSelectedTeam] = useState<string>("All");
  const { data: me } = useMe();
  const isManager = me?.role === "admin" || me?.role === "manager";
  const isAdmin = me?.role === "admin";

  async function loadData(team?: string) {
    if (!isManager) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const path = team && team !== "All" ? `/api/reports?team=${team}` : "/api/reports";
      const json = await apiFetch<{ data: Report[] }>(path);
      setReports(json.data || []);
    } catch (err) {
      toast.error("Không thể tải danh sách báo cáo.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (me?.role && isManager) loadData(selectedTeam);
  }, [me?.role, selectedTeam]);

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

  const teams = ["All", ...ALL_TEAMS];
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 max-w-4xl mx-auto">
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

        {isAdmin ? (
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <select
              className="border-border bg-white text-sm rounded-lg py-2 px-3 focus:outline-none focus:ring-2 focus:ring-xanh-green/50"
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
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center p-12 border border-border rounded-2xl bg-white text-muted-foreground shadow-sm">
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
                className={`rounded-2xl border bg-white shadow-[var(--shadow-card)] overflow-hidden ${hasCritical ? "border-red-500/50 shadow-red-500/10" : hasWarning ? "border-amber-500/50 shadow-amber-500/10" : "border-border"}`}
              >
                <div
                  className={`p-5 border-b border-border flex justify-between items-center ${hasCritical ? "bg-red-50" : hasWarning ? "bg-amber-50" : "bg-muted/5"}`}
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
                  </div>
                </div>
                <div className="p-6 prose prose-sm max-w-none prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-a:text-xanh-green prose-headings:text-xanh-deep text-slate-700">
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
