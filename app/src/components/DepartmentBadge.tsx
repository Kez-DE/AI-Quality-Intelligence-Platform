import { Building2 } from "lucide-react";
import { ROLE_LABELS, type Me } from "@/lib/api";

// Màu nhận diện riêng cho từng phòng ban (light + dark thân thiện).
const DEPT_STYLE: Record<string, string> = {
  IT: "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-500/10 dark:text-yellow-300 dark:border-yellow-500/30",
  CSKH: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-500/10 dark:text-purple-300 dark:border-purple-500/30",
  "Vận hành": "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/30",
  "Tài chính & Thanh toán":
    "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30",
  "Sản phẩm":
    "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-500/10 dark:text-orange-300 dark:border-orange-500/30",
  "Quản lý Rủi ro & Gian lận":
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-300 dark:border-red-500/30",
};

const ADMIN_STYLE =
  "bg-xanh-deep/10 text-xanh-deep border-xanh-deep/20 dark:bg-xanh-mint/10 dark:text-xanh-mint dark:border-xanh-mint/30";

/** Ô định danh phòng ban hiển thị ở góc trên bên phải.
 *  - admin: hiện "Toàn hệ thống" (xem mọi phòng).
 *  - manager/staff đã gán phòng: hiện tên phòng + màu riêng.
 *  - guest hoặc ops chưa gán phòng: không hiện (trả null) — UI khác. */
export function DepartmentBadge({ me, className = "" }: { me: Me | null | undefined; className?: string }) {
  if (!me || me.role === "guest") return null;

  const isAdmin = me.role === "admin";
  if (!isAdmin && !me.department) return null;

  const label = isAdmin ? "Toàn hệ thống" : me.department!;
  const style = isAdmin ? ADMIN_STYLE : DEPT_STYLE[me.department!] ?? ADMIN_STYLE;

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${style} ${className}`}
      title={`${ROLE_LABELS[me.role]} · ${label}`}
    >
      <Building2 className="h-3.5 w-3.5" />
      <span className="whitespace-nowrap">{label}</span>
    </div>
  );
}
