// Supabase Auth for optional Customer accounts (US-078). Only auth is used here:
// every data read and write goes through the backend with the access token.
// Without the two build-time env vars the site still works, logged out only.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;

/** What an auth redirect put in the URL: the access token of a password-recovery
 *  link, and the error code of a failed OAuth, confirmation or reset link. */
export function parseCallback(search: string, hash: string) {
  const p = new URLSearchParams(`${search.slice(1)}&${hash.slice(1)}`);
  return {
    recoveryToken: p.get("type") === "recovery" ? p.get("access_token") : null,
    error: p.get("error_code") ?? p.get("error"),
  };
}

// Read before createClient: auth-js clears the fragment once it has the session.
// AuthProvider consumes `error` once.
export const authCallback: { recoveryToken: string | null; error: string | null } = parseCallback(
  window.location.search,
  window.location.hash,
);

export const supabase: SupabaseClient | null =
  url && key
    ? createClient(url, key, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } })
    : null;

/** Where Supabase sends the browser back to after OAuth, sign-up or a reset email. */
export function redirectTo(path = "/"): string {
  return `${window.location.origin}${path}`;
}

/** Vietnamese copy for a Supabase Auth error. Its own messages are English. */
export function authErrorText(err: unknown): string {
  const e = err as { code?: string; status?: number; message?: string } | null;
  switch (e?.code) {
    case "invalid_credentials":
      return "Email hoặc mật khẩu không đúng.";
    case "email_not_confirmed":
      return "Email chưa được xác nhận. Mở thư xác nhận trong hộp thư của bạn.";
    case "user_already_exists":
    case "email_exists":
      return "Email này đã có tài khoản. Hãy đăng nhập.";
    case "weak_password":
      return "Mật khẩu chưa đủ mạnh.";
    case "same_password":
      return "Mật khẩu mới phải khác mật khẩu cũ.";
    case "otp_expired":
      return "Liên kết đã hết hạn hoặc đã được dùng. Vui lòng yêu cầu liên kết mới.";
    case "over_email_send_rate_limit":
    case "over_request_rate_limit":
      return "Bạn đã thao tác quá nhiều lần. Vui lòng thử lại sau ít phút.";
  }
  if (e?.status === 429) return "Bạn đã thao tác quá nhiều lần. Vui lòng thử lại sau ít phút.";
  return "Không thực hiện được. Vui lòng thử lại sau ít phút.";
}
