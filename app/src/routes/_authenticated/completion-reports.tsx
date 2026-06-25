import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useCallback } from "react";
import {
  ClipboardCheck,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
  User as UserIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useMe, apiFetch, isUnassignedOps } from "@/lib/api";
import { NoDepartmentNotice } from "@/components/NoDepartmentNotice";

export const Route = createFileRoute("/_authenticated/completion-reports")({
  component: CompletionReportsPage,
});

type CompletionReport = {
  id: string;
  task_id: string;
  staff_email: string | null;
  team: string;
  completion_level: "completed" | "partial" | "blocked";
  note: string;
  status: "submitted" | "approved" | "rejected";
  review_note: string | null;
  reviewed_at: string | null;
  created_at: string;
};

const STATUS_TABS = [
  { v: "submitted", l: "Chờ duyệt" },
  { v: "approved", l: "Đã duyệt" },
  { v: "rejected", l: "Trả lại" },
  { v: "all", l: "Tất cả" },
] as const;

const LEVEL_META: Record<string, { label: string; cls: string }> = {
  completed: { label: "Hoàn thành", cls: "bg-green-100 text-green-800" },
  partial: { label: "Một phần", cls: "bg-amber-100 text-amber-800" },
  blocked: { label: "Bị chặn", cls: "bg-red-100 text-red-700" },
};

const STATUS_META: Record<string, { label: string; cls: string }> = {
  submitted: { label: "Chờ duyệt", cls: "bg-blue-100 text-blue-800" },
  approved: { label: "Đã duyệt", cls: "bg-green-100 text-green-800" },
  rejected: { label: "Trả lại", cls: "bg-red-100 text-red-700" },
};

function CompletionReportsPage() {
  const { data: me } = useMe();
  const canReview = me?.role === "admin" || me?.role === "manager";

  const [reports, setReports] = useState<CompletionReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("submitted");
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({});
  const [acting, setActing] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!canReview) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "100");
      if (filterStatus !== "all") params.set("status", filterStatus);
      const json = await apiFetch<{ data: CompletionReport[] }>(
        `/api/completion-reports?${params.toString()}`,
      );
      setReports(json.data || []);
    } catch {
      toast.error("Không thể tải danh sách báo cáo hoàn thành.");
    } finally {
      setLoading(false);
    }
  }, [canReview, filterStatus]);

  useEffect(() => {
    if (me?.role) loadData();
  }, [me?.role, loadData]);

  async function review(reportId: string, status: "approved" | "rejected") {
    setActing(reportId);
    try {
      await apiFetch(`/api/completion-reports/${reportId}/review`, {
        method: "PATCH",
        body: JSON.stringify({
          status,
          review_note: reviewNote[reportId] || null,
        }),
      });
      toast.success(
        status === "approved"
          ? "Đã duyệt báo cáo — task chuyển sang Đã xong."
          : "Đã trả lại báo cáo — task quay lại Đang xử lý.",
      );
      setReports((prev) =>
        prev.map((r) => (r.id === reportId ? { ...r, status } : r)),
      );
      // Nếu đang lọc theo trạng thái cụ thể, loại khỏi danh sách hiện tại.
      if (filterStatus !== "all") {
        setReports((prev) => prev.filter((r) => r.id !== reportId));
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Lỗi khi duyệt báo cáo.");
    } finally {
      setActing(null);
    }
  }

  if (!canReview) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Chỉ quản lý hoặc admin được xem trang Báo cáo hoàn thành.
      </div>
    );
  }

  if (isUnassignedOps(me)) {
    return (
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <ClipboardCheck className="h-8 w-8 text-xanh-deep" />
          Báo cáo hoàn thành
        </h1>
        <NoDepartmentNotice />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
      <div>
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <ClipboardCheck className="h-8 w-8 text-xanh-deep" />
          Báo cáo hoàn thành
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Theo dõi và duyệt báo cáo hoàn thành do nhân viên gửi sau khi xử lý công việc.
        </p>
      </div>

      {/* Status filter */}
      <div className="rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-xanh-deep mb-3">
          <Filter className="h-4 w-4" />
          Lọc theo trạng thái
        </div>
        <div className="flex rounded-lg border border-border overflow-hidden w-fit">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.v}
              onClick={() => setFilterStatus(tab.v)}
              className={`px-4 py-1.5 text-xs font-semibold transition-colors ${
                filterStatus === tab.v
                  ? "bg-xanh-deep text-white"
                  : "bg-card text-muted-foreground hover:bg-muted/30"
              }`}
            >
              {tab.l}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-xanh-green" />
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center p-12 border border-border rounded-2xl bg-card text-muted-foreground shadow-sm">
          Không có báo cáo nào trong trạng thái này.
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((r) => {
            const level = LEVEL_META[r.completion_level] || LEVEL_META.completed;
            const status = STATUS_META[r.status] || STATUS_META.submitted;
            return (
              <div
                key={r.id}
                className="rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] p-5 space-y-3"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${level.cls}`}
                  >
                    {level.label}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${status.cls}`}
                  >
                    {status.label}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                    {r.team}
                  </span>
                  <span className="text-[11px] font-mono text-muted-foreground flex items-center gap-1">
                    <UserIcon className="h-3 w-3" /> {r.staff_email || "N/A"}
                  </span>
                  <span className="text-[11px] font-mono text-muted-foreground flex items-center gap-1 ml-auto">
                    <Clock className="h-3 w-3" />
                    {new Date(r.created_at).toLocaleString("vi-VN")}
                  </span>
                </div>

                <p className="text-sm text-foreground whitespace-pre-wrap bg-muted/20 rounded-lg p-3 border border-border">
                  {r.note}
                </p>

                {r.review_note && (
                  <p className="text-xs text-muted-foreground">
                    <span className="font-semibold">Ghi chú duyệt:</span> {r.review_note}
                  </p>
                )}

                {r.status === "submitted" && (
                  <div className="space-y-2 pt-1">
                    <input
                      type="text"
                      value={reviewNote[r.id] || ""}
                      onChange={(e) =>
                        setReviewNote((prev) => ({ ...prev, [r.id]: e.target.value }))
                      }
                      placeholder="Ghi chú phản hồi cho nhân viên (tuỳ chọn)..."
                      className="w-full px-3 py-2 text-xs border border-border rounded-lg bg-card focus:outline-none focus:ring-2 focus:ring-xanh-green/30"
                    />
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => review(r.id, "rejected")}
                        disabled={acting === r.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded-lg text-xs font-semibold hover:bg-red-100 transition-colors disabled:opacity-50"
                      >
                        <XCircle className="h-4 w-4" /> Trả lại
                      </button>
                      <button
                        onClick={() => review(r.id, "approved")}
                        disabled={acting === r.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-xanh-deep text-white rounded-lg text-xs font-semibold hover:bg-xanh-deep/90 transition-colors disabled:opacity-50"
                      >
                        {acting === r.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        Duyệt
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
