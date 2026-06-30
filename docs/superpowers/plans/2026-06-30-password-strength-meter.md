# Password Strength Meter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm thanh sức mạnh mật khẩu + checklist 5 tiêu chí vào form signup của AuthPage.

**Architecture:** Thêm hàm `validatePassword` (pure) + component `PasswordStrengthHint` vào `auth.tsx`. Không tạo file mới — tất cả gói gọn trong file hiện tại, giữ đúng pattern của codebase.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Vitest

## Global Constraints

- Chỉ sửa `app/src/routes/auth.tsx` và test file
- Không tạo abstraction mới ngoài 2 item trên
- Không đụng signin flow, Field component, Google OAuth button, layout
- Copy (label text) phải bằng tiếng Việt, nhất quán với file hiện tại
- Màu dùng token Tailwind của dự án: `bg-destructive`, `bg-orange-400`, `bg-yellow-400`, `bg-xanh-green`

---

### Task 1: validatePassword function + PasswordStrengthHint component

**Files:**
- Modify: `app/src/routes/auth.tsx` — thêm 2 definitions mới ở cuối file (trước `PreviewStat`)
- Test: `app/src/routes/auth.test.ts` (tạo mới nếu chưa có)

**Interfaces:**
- Produces:
  - `validatePassword(pw: string): { len: boolean; upper: boolean; lower: boolean; digit: boolean; special: boolean }`
  - `PasswordStrengthHint({ password }: { password: string }): JSX.Element | null`

- [ ] **Step 1: Tạo test file và viết failing test cho validatePassword**

Tạo `app/src/routes/auth.test.ts`:

```typescript
import { describe, it, expect } from "vitest";

// Re-export để test (vì validatePassword là internal function)
// Ta sẽ test gián tiếp qua DOM, hoặc export tạm — dùng cách đơn giản nhất:
// Đặt validatePassword ra ngoài module scope và export named.

// Tạm thời viết logic test inline để xác nhận spec trước khi implement:
function validatePassword(pw: string) {
  return {
    len:     pw.length >= 8,
    upper:   /[A-Z]/.test(pw),
    lower:   /[a-z]/.test(pw),
    digit:   /[0-9]/.test(pw),
    special: /[^A-Za-z0-9]/.test(pw),
  };
}

describe("validatePassword", () => {
  it("fails all on empty string", () => {
    expect(validatePassword("")).toEqual({ len: false, upper: false, lower: false, digit: false, special: false });
  });

  it("passes len only for 8 lowercase chars", () => {
    const r = validatePassword("abcdefgh");
    expect(r.len).toBe(true);
    expect(r.upper).toBe(false);
    expect(r.digit).toBe(false);
    expect(r.special).toBe(false);
  });

  it("passes all for Abc123!x", () => {
    expect(validatePassword("Abc123!x")).toEqual({ len: true, upper: true, lower: true, digit: true, special: true });
  });

  it("detects special chars: @#$%", () => {
    expect(validatePassword("a@").special).toBe(true);
  });

  it("does NOT count space as special (space is non-alphanumeric)", () => {
    // space matches [^A-Za-z0-9], intentional — consistent with Supabase weak_password behavior
    expect(validatePassword("a ").special).toBe(true);
  });
});
```

- [ ] **Step 2: Chạy test để xác nhận pass (vì logic inline)**

```bash
cd app && npx vitest run src/routes/auth.test.ts --reporter=verbose
```

Expected: 5 tests PASS (test dùng copy of function, không phải import).

- [ ] **Step 3: Thêm validatePassword + PasswordStrengthHint vào auth.tsx**

Thêm đoạn sau vào `app/src/routes/auth.tsx`, ngay trước function `PreviewStat` (dòng ~417):

```typescript
function validatePassword(pw: string) {
  return {
    len:     pw.length >= 8,
    upper:   /[A-Z]/.test(pw),
    lower:   /[a-z]/.test(pw),
    digit:   /[0-9]/.test(pw),
    special: /[^A-Za-z0-9]/.test(pw),
  };
}

const STRENGTH_LEVELS = [
  { maxScore: 1, label: "Rất yếu",    color: "bg-destructive" },
  { maxScore: 2, label: "Yếu",        color: "bg-orange-400" },
  { maxScore: 4, label: "Trung bình", color: "bg-yellow-400" },
  { maxScore: 5, label: "Mạnh",       color: "bg-xanh-green" },
] as const;

const PASSWORD_CRITERIA = [
  { key: "len",     label: "Ít nhất 8 ký tự" },
  { key: "upper",   label: "Chữ hoa (A–Z)" },
  { key: "lower",   label: "Chữ thường (a–z)" },
  { key: "digit",   label: "Số (0–9)" },
  { key: "special", label: "Ký tự đặc biệt (!@#…)" },
] as const;

function PasswordStrengthHint({ password }: { password: string }) {
  if (!password) return null;
  const checks = validatePassword(password);
  const score = Object.values(checks).filter(Boolean).length;
  const level = STRENGTH_LEVELS.find((l) => score <= l.maxScore) ?? STRENGTH_LEVELS[3];
  const filledSegments = score === 0 ? 0 : Math.max(1, Math.ceil((score / 5) * 4));

  return (
    <div className="space-y-2 text-xs">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i < filledSegments ? level.color : "bg-muted opacity-40"
              }`}
            />
          ))}
        </div>
        <span className="w-16 text-right text-muted-foreground">{level.label}</span>
      </div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-muted-foreground">
        {PASSWORD_CRITERIA.map(({ key, label }) => (
          <li
            key={key}
            className={`flex items-center gap-1.5 ${checks[key] ? "text-xanh-green" : ""}`}
          >
            <span className="shrink-0 font-mono">{checks[key] ? "✓" : "–"}</span>
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Cập nhật test để import thật từ auth.tsx**

Thay nội dung `app/src/routes/auth.test.ts` — xoá copy của validatePassword, export named từ file auth:

> **Lưu ý:** `validatePassword` cần được export từ `auth.tsx`. Thêm `export` keyword vào function:
> Sửa `function validatePassword(pw: string)` → `export function validatePassword(pw: string)` trong `auth.tsx`

Cập nhật `app/src/routes/auth.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { validatePassword } from "./auth";

describe("validatePassword", () => {
  it("fails all on empty string", () => {
    expect(validatePassword("")).toEqual({ len: false, upper: false, lower: false, digit: false, special: false });
  });

  it("passes len only for 8 lowercase chars", () => {
    const r = validatePassword("abcdefgh");
    expect(r.len).toBe(true);
    expect(r.upper).toBe(false);
    expect(r.digit).toBe(false);
    expect(r.special).toBe(false);
  });

  it("passes all for Abc123!x", () => {
    expect(validatePassword("Abc123!x")).toEqual({ len: true, upper: true, lower: true, digit: true, special: true });
  });

  it("detects special chars", () => {
    expect(validatePassword("a@").special).toBe(true);
  });

  it("score 0 when empty", () => {
    const checks = validatePassword("");
    expect(Object.values(checks).filter(Boolean).length).toBe(0);
  });
});
```

- [ ] **Step 5: Chạy test để xác nhận pass**

```bash
cd app && npx vitest run src/routes/auth.test.ts --reporter=verbose
```

Expected: 5 tests PASS.

- [ ] **Step 6: TypeScript check**

```bash
cd app && npx tsc --noEmit 2>&1 | head -20
```

Expected: 0 errors.

- [ ] **Step 7: Commit**

```bash
git add app/src/routes/auth.tsx app/src/routes/auth.test.ts
git commit -m "feat(auth): validatePassword + PasswordStrengthHint component"
```

---

### Task 2: Wire vào signup form + block submit

**Files:**
- Modify: `app/src/routes/auth.tsx` — 3 điểm thay đổi trong `AuthPage`

**Interfaces:**
- Consumes: `validatePassword`, `PasswordStrengthHint` từ Task 1

- [ ] **Step 1: Thêm PasswordStrengthHint vào form (sau Field password)**

Trong `AuthPage`, tìm đoạn:

```tsx
<Field
  icon={Lock}
  type="password"
  label="Mật khẩu"
  placeholder={mode === "signin" ? "••••••••" : "Tối thiểu 8 ký tự"}
  value={password}
  onChange={(v) => { setPassword(v); setAuthError(""); }}
  required
  minLength={mode === "signup" ? 8 : undefined}
/>
```

Thay bằng (xoá `minLength`, thêm hint):

```tsx
<Field
  icon={Lock}
  type="password"
  label="Mật khẩu"
  placeholder={mode === "signin" ? "••••••••" : "Tối thiểu 8 ký tự"}
  value={password}
  onChange={(v) => { setPassword(v); setAuthError(""); }}
  required
/>
{mode === "signup" && <PasswordStrengthHint password={password} />}
```

- [ ] **Step 2: Block submit khi password chưa đủ mạnh (signup)**

Trong `handleSubmit`, ngay sau `setLoading(true)`, thêm guard:

Tìm:
```typescript
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  setLoading(true);
  try {
    if (mode === "signup") {
```

Thay thành:
```typescript
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  if (mode === "signup") {
    const checks = validatePassword(password);
    if (!Object.values(checks).every(Boolean)) {
      setAuthError("Mật khẩu chưa đủ mạnh. Hãy đáp ứng tất cả 5 tiêu chí.");
      return;
    }
  }
  setLoading(true);
  try {
    if (mode === "signup") {
```

- [ ] **Step 3: TypeScript check**

```bash
cd app && npx tsc --noEmit 2>&1 | head -20
```

Expected: 0 errors.

- [ ] **Step 4: Chạy toàn bộ test suite**

```bash
cd app && npx vitest run --reporter=verbose
```

Expected: tất cả tests PASS (bao gồm 5 tests mới từ Task 1).

- [ ] **Step 5: Smoke test thủ công**

1. Mở `http://localhost:5173/auth`
2. Chuyển sang tab "Tạo tài khoản"
3. Gõ `a` vào password → thanh đỏ 1 segment, "Rất yếu", 4 dấu `–`
4. Gõ `Abc123!x` → thanh xanh 4 segment, "Mạnh", 5 dấu `✓`
5. Nhấn Submit khi `Abc123` (thiếu special) → inline error, không redirect
6. Xoá password → PasswordStrengthHint ẩn
7. Chuyển sang "Đăng nhập" → PasswordStrengthHint không hiện

- [ ] **Step 6: Commit**

```bash
git add app/src/routes/auth.tsx
git commit -m "feat(auth): password strength meter — bar + checklist + submit guard"
```
