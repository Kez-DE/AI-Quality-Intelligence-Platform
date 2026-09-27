// Password criteria shared by the admin "Tạo tài khoản" form and the first-login
// change-password screen. The backend (POST /api/admin/users) enforces the same
// 5 rules, so keep the two sides in sync.

export function validatePassword(pw: string) {
  return {
    len: pw.length >= 8,
    upper: /[A-Z]/.test(pw),
    lower: /[a-z]/.test(pw),
    digit: /[0-9]/.test(pw),
    special: /[^A-Za-z0-9]/.test(pw),
  };
}

export function isStrongPassword(pw: string): boolean {
  return Object.values(validatePassword(pw)).every(Boolean);
}

export const PASSWORD_CRITERIA = [
  { key: "len", label: "Ít nhất 8 ký tự" },
  { key: "upper", label: "Chữ hoa (A–Z)" },
  { key: "lower", label: "Chữ thường (a–z)" },
  { key: "digit", label: "Số (0–9)" },
  { key: "special", label: "Ký tự đặc biệt (!@#…)" },
] as const;
