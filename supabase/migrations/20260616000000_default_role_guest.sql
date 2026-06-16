-- Thay đổi cơ chế đăng ký: tài khoản mới mặc định là 'guest'
-- Tài khoản đầu tiên đăng ký vẫn là 'admin'
-- Nhân viên sẽ cần được admin chuyển quyền (role='staff' hoặc 'manager') trên giao diện quản lý.

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
    assigned_role := 'guest';
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
