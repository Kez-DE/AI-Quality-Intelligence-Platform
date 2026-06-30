# Spec: Password Strength Meter — AuthPage signup

**Date:** 2026-06-30  
**Lane:** Normal (Auth hard gate, scope hẹp — UI-only, không đụng backend/JWT)  
**File affected:** `app/src/routes/auth.tsx`

## Vấn đề

Form signup chỉ có `minLength={8}` trên HTML input — không có visual feedback. User không biết mật khẩu của mình đã đủ mạnh chưa cho đến khi nhấn Submit và nhận lỗi `weak_password` từ Supabase.

## Yêu cầu

### 1. Hàm validatePassword

```ts
function validatePassword(pw: string) {
  return {
    len:     pw.length >= 8,
    upper:   /[A-Z]/.test(pw),
    lower:   /[a-z]/.test(pw),
    digit:   /[0-9]/.test(pw),
    special: /[^A-Za-z0-9]/.test(pw),
  };
}
```

Trả về object 5 boolean. Dùng chung cho thanh + checklist.

### 2. Tính điểm sức mạnh

```ts
const score = Object.values(checks).filter(Boolean).length; // 0–5
```

Mapping điểm → label + màu:

| Score | Label | Màu Tailwind |
|---|---|---|
| 0–1 | Rất yếu | `bg-destructive` (đỏ) |
| 2 | Yếu | `bg-orange-400` |
| 3–4 | Trung bình | `bg-yellow-400` |
| 5 | Mạnh | `bg-xanh-green` |

### 3. Component PasswordStrengthHint

Props: `password: string`

Render khi `password.length > 0`, gồm 2 phần:

**A. Thanh sức mạnh** — 4 segment nhỏ nằm ngang:
- Segment sáng màu nếu `index < Math.ceil(score / 5 * 4)`
- Segment tối (opacity-20) nếu không
- Nhãn label hiện bên phải thanh (text-xs)

**B. Checklist** — 5 dòng text-xs:
- `✓` text-xanh-green khi criterion = true
- `–` text-muted-foreground khi false

Nội dung checklist:
1. Ít nhất 8 ký tự
2. Chữ hoa (A–Z)
3. Chữ thường (a–z)
4. Số (0–9)
5. Ký tự đặc biệt (!@#...)

### 4. Vị trí trong form

Render `<PasswordStrengthHint password={password} />` ngay sau `<Field ... type="password" .../>`, chỉ khi `mode === "signup"`.

### 5. Block submit

Trong `handleSubmit`, nếu `mode === "signup"` và không phải tất cả 5 tiêu chí đều true: set `authError` = "Mật khẩu chưa đủ mạnh. Hãy đáp ứng tất cả 5 tiêu chí." và return sớm. Không gọi Supabase.

## Không thay đổi

- `Field` component — giữ nguyên, không nhận prop mới
- `getAuthErrorMessage` — giữ nguyên `weak_password` case (fallback từ Supabase)
- Signin mode — không có strength meter
- Layout, brand panel, Google OAuth button — giữ nguyên

## Validation

- Gõ `abc` → score 1 → thanh đỏ 1/4, "Rất yếu"
- Gõ `Abc123!x` → score 5 → thanh xanh 4/4, "Mạnh", tất cả 5 ✓
- Nhấn Submit khi score < 5 (signup) → inline error, không gọi Supabase
- Chuyển sang signin → PasswordStrengthHint ẩn
- `password = ""` → PasswordStrengthHint ẩn
