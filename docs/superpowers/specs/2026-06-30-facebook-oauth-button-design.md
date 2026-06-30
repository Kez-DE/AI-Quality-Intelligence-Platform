# Spec: Facebook OAuth Button — AuthPage

**Date:** 2026-06-30
**Lane:** Normal (Auth hard gate, scope hẹp — UI-only, thêm provider đã cấu hình trên Supabase)
**File affected:** `app/src/routes/auth.tsx`

## Bối cảnh

Facebook OAuth đã được cấu hình trên Supabase Dashboard. Cần thêm nút Facebook vào trang auth, đặt cạnh nút Google hiện có.

## Yêu cầu

### Layout

Thay thế nút Google full-width hiện tại bằng một hàng `grid grid-cols-2 gap-2.5`:

```
[ Google ]  [ Facebook ]
```

Wrapper:
```tsx
<div className="grid grid-cols-2 gap-2.5">
  {/* Google button */}
  {/* Facebook button */}
</div>
```

### Google button (giữ nguyên logic, chỉ bỏ `w-full`)

Style: `flex items-center justify-center gap-2.5 rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium transition hover:bg-muted`

### Facebook button (mới)

```tsx
<button
  type="button"
  onClick={() =>
    supabase.auth.signInWithOAuth({
      provider: "facebook",
      options: { redirectTo: window.location.origin + "/dashboard" },
    })
  }
  className="flex items-center justify-center gap-2.5 rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium transition hover:bg-muted"
>
  <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden>
    <path
      fill="#1877F2"
      d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.236 2.686.236v2.97h-1.514c-1.491 0-1.956.93-1.956 1.886v2.267h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"
    />
  </svg>
  Facebook
</button>
```

### Behavior

- Dùng chung cả signin và signup mode (giống Google)
- Sau khi Facebook redirect về `/dashboard`, Supabase client tự exchange PKCE code qua `getSession()` trong `/_authenticated/route.tsx`'s `beforeLoad` — không cần route callback mới

## Không thay đổi

- Divider "hoặc" — giữ nguyên
- Google OAuth logic — chỉ co vào grid
- Form, error handling, layout tổng thể — giữ nguyên

## Validation

- Trang auth hiển thị 2 nút side-by-side trong 1 hàng
- Nhấn "Facebook" → redirect đến Facebook OAuth
- Sau Facebook auth → trở về `/dashboard`, đăng nhập thành công
- Nút Google vẫn hoạt động như cũ
