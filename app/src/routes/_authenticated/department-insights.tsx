import { createFileRoute, Link } from "@tanstack/react-router";
import { Building2, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/_authenticated/department-insights")({
  component: DepartmentInsightsRedirect,
});

function DepartmentInsightsRedirect() {
  return (
    <div className="rounded-2xl border border-border bg-white p-8 shadow-[var(--shadow-card)] space-y-4">
      <div className="flex items-center gap-2">
        <Building2 className="h-6 w-6 text-xanh-green" />
        <h1 className="font-display text-2xl font-bold">Phân tích phòng ban đã được gộp</h1>
      </div>
      <p className="text-sm text-muted-foreground max-w-2xl">
        Route cũ <code>/department-insights</code> đã được thay bằng trang chuẩn <code>/insights</code>.
        Trang mới tải metric 6 phòng ban nhanh và chỉ gọi LLM khi bấm phân tích sâu cho từng phòng.
      </p>
      <Link
        to="/insights"
        className="inline-flex h-10 items-center gap-2 rounded-xl bg-xanh-deep px-4 text-sm font-semibold text-white hover:opacity-90"
      >
        Mở trang Phân tích phòng ban
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
