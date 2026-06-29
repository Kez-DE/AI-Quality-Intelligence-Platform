# Spec: Google OAuth button + Inline auth error — AuthPage

**Date:** 2026-06-29
**Lane:** Normal (Auth hard gate, scope hẹp, user xác nhận)
**File affected:** `app/src/routes/auth.tsx`

## Vấn đề

1. Lỗi sai mật khẩu chỉ hiện qua sonner toast — dễ bỏ qua, không rõ ràng.
2. Chưa có nút đăng nhập nhanh bằng Google — phải nhập email/password thủ công.

## Yêu cầu

### 1. Inline auth error
- Thêm `authError` state (`string`).
- Khi `handleSubmit` catch lỗi: set `authError` = `getAuthErrorMessage(err)` (giữ toast).
- Clear `authError` khi: user gõ email/password, hoặc đổi mode (signin ↔ signup).
- Render: khối đỏ nhỏ trên nút submit, cùng pattern với khối `confirmationEmail` (icon + text).

### 2. Google OAuth button
- Thêm hàm `handleGoogleSignIn` gọi:
  ```ts
  supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin + '/dashboard' },
  })
  ```
- Đặt dưới nút submit, phân cách bằng divider `<hr> hoặc <hr>`.
- Style: nền card/trắng, viền border, Google SVG icon + text "Tiếp tục bằng Google".
- Dùng chung cả sign-in và sign-up mode.
- Sau khi Google redirect về `/dashboard`, Supabase client tự exchange PKCE code qua `getSession()` trong `/_authenticated/route.tsx`'s `beforeLoad` — không cần route callback mới.

## Không thay đổi

- `getAuthErrorMessage` — giữ nguyên.
- `Field` component — giữ nguyên.
- Toàn bộ layout, brand panel, mobile header — giữ nguyên.
- Toast vẫn hiện kèm inline error (redundancy chấp nhận được).

## Validation

- Nhập sai mật khẩu → khối đỏ inline hiện ngay dưới form, không chỉ toast.
- Nhập lại email hoặc password → khối đỏ tự ẩn.
- Nhấn "Tiếp tục bằng Google" → redirect đến Google OAuth.
- Sau Google auth → trở về `/dashboard`, đăng nhập thành công.
