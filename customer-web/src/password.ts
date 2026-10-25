// Copied from app/src/lib/password.ts (the Staff web). The backend enforces the
// same 5 rules for admin-created accounts; keep all three in sync.

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
