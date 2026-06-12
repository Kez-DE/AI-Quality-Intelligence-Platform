-- ============================================================
-- RBAC: 4 roles (admin / manager / staff / guest)
-- ============================================================
-- Business model note:
--   - admin   : toàn quyền + quản lý user (đổi role, xoá user).
--   - manager : xem toàn bộ feedback/alerts của hệ thống (ops cockpit).
--   - staff   : xem toàn bộ feedback/alerts + xử lý ticket.
--   - guest   : chỉ xem dữ liệu của chính mình (read-only nghiệp vụ).
--
-- Backend FastAPI dùng SERVICE_ROLE_KEY nên bypass RLS — các policy dưới đây
-- áp dụng cho truy cập Supabase TRỰC TIẾP từ frontend (chat, realtime, insert).

-- 1) Thêm cột role vào profiles
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'staff'
  CHECK (role IN ('admin', 'manager', 'staff', 'guest'));

-- 2) Helper: đọc role của user hiện tại.
--    SECURITY DEFINER + search_path cố định => bỏ qua RLS của profiles,
--    nhờ vậy policy gọi hàm này KHÔNG gây đệ quy vô hạn.
CREATE OR REPLACE FUNCTION public.current_user_role()
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT role FROM public.profiles WHERE id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT public.current_user_role() = 'admin';
$$;

-- staff/manager/admin = nhân sự vận hành, được xem dữ liệu toàn hệ thống.
CREATE OR REPLACE FUNCTION public.is_ops_staff()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT public.current_user_role() IN ('admin', 'manager', 'staff');
$$;

-- 3) Profiles policies: admin xem/sửa tất cả; user thường xem/sửa của mình.
DROP POLICY IF EXISTS "Users view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users update own profile" ON public.profiles;
DROP POLICY IF EXISTS "Profiles select" ON public.profiles;
DROP POLICY IF EXISTS "Profiles update" ON public.profiles;

CREATE POLICY "Profiles select" ON public.profiles
  FOR SELECT TO authenticated
  USING (auth.uid() = id OR public.is_admin());

CREATE POLICY "Profiles update" ON public.profiles
  FOR UPDATE TO authenticated
  USING (auth.uid() = id OR public.is_admin())
  WITH CHECK (auth.uid() = id OR public.is_admin());

-- Policy chỉ giới hạn hàng, không giới hạn cột. Thu hồi UPDATE toàn bảng để
-- user thường không thể tự đổi role qua Supabase REST; profile chỉ cho sửa tên.
-- Admin đổi role qua FastAPI dùng service_role nên không bị giới hạn này.
REVOKE UPDATE ON public.profiles FROM authenticated;
GRANT UPDATE (full_name) ON public.profiles TO authenticated;

-- 4) Feedback: ops staff xem toàn bộ; guest chỉ xem của mình.
--    Giữ quyền ghi của chính chủ; bổ sung quyền đọc theo role.
DROP POLICY IF EXISTS "Users manage own feedback" ON public.feedback;
DROP POLICY IF EXISTS "Feedback select" ON public.feedback;
DROP POLICY IF EXISTS "Feedback insert own" ON public.feedback;
DROP POLICY IF EXISTS "Feedback update own or ops" ON public.feedback;
DROP POLICY IF EXISTS "Feedback delete own or admin" ON public.feedback;

CREATE POLICY "Feedback select" ON public.feedback
  FOR SELECT TO authenticated
  USING (auth.uid() = user_id OR public.is_ops_staff());

CREATE POLICY "Feedback insert own" ON public.feedback
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Feedback update own or ops" ON public.feedback
  FOR UPDATE TO authenticated
  USING (auth.uid() = user_id OR public.is_ops_staff())
  WITH CHECK (auth.uid() = user_id OR public.is_ops_staff());

CREATE POLICY "Feedback delete own or admin" ON public.feedback
  FOR DELETE TO authenticated
  USING (auth.uid() = user_id OR public.is_admin());

-- 5) Alerts: ops staff xem + xử lý toàn bộ; guest chỉ của mình.
DROP POLICY IF EXISTS "Users manage own alerts" ON public.alerts;
DROP POLICY IF EXISTS "Alerts select" ON public.alerts;
DROP POLICY IF EXISTS "Alerts insert own" ON public.alerts;
DROP POLICY IF EXISTS "Alerts update own or ops" ON public.alerts;
DROP POLICY IF EXISTS "Alerts delete own or admin" ON public.alerts;

CREATE POLICY "Alerts select" ON public.alerts
  FOR SELECT TO authenticated
  USING (auth.uid() = user_id OR public.is_ops_staff());

CREATE POLICY "Alerts insert own" ON public.alerts
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Alerts update own or ops" ON public.alerts
  FOR UPDATE TO authenticated
  USING (auth.uid() = user_id OR public.is_ops_staff())
  WITH CHECK (auth.uid() = user_id OR public.is_ops_staff());

CREATE POLICY "Alerts delete own or admin" ON public.alerts
  FOR DELETE TO authenticated
  USING (auth.uid() = user_id OR public.is_admin());

-- 6) Bootstrap: user đăng ký ĐẦU TIÊN trở thành admin, còn lại mặc định staff.
--    Thuận tiện cho demo/chấm điểm: không cần can thiệp DB thủ công.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  assigned_role TEXT;
BEGIN
  IF (SELECT COUNT(*) FROM public.profiles) = 0 THEN
    assigned_role := 'admin';
  ELSE
    assigned_role := 'staff';
  END IF;

  INSERT INTO public.profiles (id, email, full_name, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    assigned_role
  );
  RETURN NEW;
END;
$$;

-- Project có thể đã có user trước khi migration RBAC được áp dụng. Khi chưa có
-- admin, bootstrap profile cũ nhất để trang quản trị có tài khoản khởi đầu.
UPDATE public.profiles
SET role = 'admin'
WHERE id = (
  SELECT id
  FROM public.profiles
  ORDER BY created_at ASC
  LIMIT 1
)
AND NOT EXISTS (
  SELECT 1 FROM public.profiles WHERE role = 'admin'
);
