import { Building2 } from "lucide-react";

/** Hiển thị khi ops user (manager/staff) chưa được gán phòng ban.
 *  Theo thiết kế RBAC: chưa gán phòng → không xem được dữ liệu phòng nào. */
export function NoDepartmentNotice() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-muted-foreground/30 bg-muted/20 px-6 py-12 text-center">
      <Building2 className="h-10 w-10 text-muted-foreground/60" />
      <h3 className="text-lg font-semibold">Chưa được gán phòng ban</h3>
      <p className="max-w-md text-sm text-muted-foreground">
        Tài khoản của bạn chưa được gán phòng ban nên chưa thể xem dữ liệu. Vui lòng liên hệ
        quản trị viên (admin) để được cấp quyền xem dữ liệu phòng ban của bạn.
      </p>
    </div>
  );
}
