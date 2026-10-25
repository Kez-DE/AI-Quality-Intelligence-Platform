import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { CUSTOMER_WEB_URL } from "@/lib/api";
import {
  Car,
  Loader2,
  Mail,
  Lock,
  ArrowRight,
  AlertCircle,
  Eye,
  EyeOff,
  Sparkles,
  Activity,
  BarChart3,
  ShieldCheck,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Đăng nhập · xanhSM Cockpit" },
      {
        name: "description",
        content:
          "Đăng nhập vào AI Quality Intelligence Cockpit của xanhSM — phân loại phản hồi, theo dõi SLA và ra quyết định nhanh.",
      },
    ],
  }),
  component: AuthPage,
});

// Staff web login only (US-077): no self sign-up, no social login. Accounts are
// created by an admin on /admin; Customers use the Customer web instead.
function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    // A Supabase auth redirect reports errors as hash params: #error=...&error_description=...
    const hash = window.location.hash.slice(1);
    if (hash) {
      const p = new URLSearchParams(hash);
      const desc = p.get("error_description") || p.get("error");
      if (desc) {
        setAuthError(getAuthErrorMessage({ message: decodeURIComponent(desc.replace(/\+/g, " ")) }));
        window.history.replaceState(null, "", window.location.pathname);
        return;
      }
    }
    // Also check sessionStorage (set by /_authenticated/route.tsx on redirect)
    const stored = sessionStorage.getItem("oauth_error");
    if (stored) {
      setAuthError(getAuthErrorMessage({ message: stored }));
      sessionStorage.removeItem("oauth_error");
      return;
    }
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) window.location.replace("/dashboard");
    });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      await supabase.auth.getSession();
      toast.success("Đăng nhập thành công");
      window.location.assign("/dashboard");
    } catch (err: any) {
      const msg = getAuthErrorMessage(err);
      setAuthError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      {/* Ambient background */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: "var(--gradient-mesh)" }}
      />

      <div className="mx-auto grid min-h-screen w-full max-w-7xl grid-cols-1 lg:grid-cols-[1.05fr_1fr] lg:gap-6 lg:p-6">
        {/* LEFT — brand panel (card nổi: bo góc + viền Aurora + quầng sáng, đồng bộ với Auth Card) */}
        <section
          className="aurora-card relative hidden flex-col justify-between overflow-hidden rounded-[2rem] p-10 text-white lg:flex"
          style={{ background: "var(--gradient-hero)" }}
        >
          <Link to="/" className="relative z-10 flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-white/15 backdrop-blur">
              <Car className="h-5 w-5" />
            </span>
            <span className="leading-tight">
              <span className="block font-display text-base font-bold">AI Quality Intelligence</span>
              <span className="block font-mono text-xs opacity-80">xanhSM · Cockpit</span>
            </span>
          </Link>

          <div className="relative z-10 max-w-md">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1 text-xs font-medium backdrop-blur">
              <Sparkles className="h-3.5 w-3.5" />
              Smart Mobility · Feedback Analytics
            </span>
            <h1 className="mt-5 font-display text-4xl font-bold leading-[1.12] tracking-tight">
              Biến hàng nghìn phản hồi mỗi ngày thành{" "}
              <span className="opacity-90">hành động vận hành</span>.
            </h1>
            <p className="mt-4 text-base opacity-90">
              Truy cập khoang lái AI: phân loại phản hồi tự động, phát hiện spike, sinh alert &
              ticket theo SLA.
            </p>

            <div className="mt-8 grid grid-cols-2 gap-3">
              <PreviewStat icon={<Activity className="h-4 w-4" />} label="Feedback/ngày" value="12,480" />
              <PreviewStat icon={<BarChart3 className="h-4 w-4" />} label="Auto-classified" value="97.4%" />
              <PreviewStat icon={<ShieldCheck className="h-4 w-4" />} label="SLA on-time" value="94%" />
              <PreviewStat icon={<Clock className="h-4 w-4" />} label="MTTD sự cố" value="4.2′" />
            </div>
          </div>

          <ul className="relative z-10 space-y-2 text-sm opacity-90">
            {[
              "Bảo mật cấp doanh nghiệp · mã hoá đầu cuối",
              "Phân quyền theo vai trò · audit log đầy đủ",
              "Đồng bộ realtime với hệ thống vận hành",
            ].map((t) => (
              <li key={t} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                {t}
              </li>
            ))}
          </ul>

          {/* decorative blobs */}
          <div className="pointer-events-none absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-white/10 blur-3xl" />
          <div className="pointer-events-none absolute top-1/4 -left-24 h-60 w-60 rounded-full bg-white/10 blur-3xl" />
        </section>

        {/* RIGHT — form */}
        <section className="flex items-center justify-center px-5 py-10 sm:px-10">
          <div className="w-full max-w-md">
            {/* Mobile brand */}
            <Link to="/" className="mb-8 flex items-center gap-3 lg:hidden">
              <span
                className="grid h-10 w-10 place-items-center rounded-xl text-white"
                style={{ background: "var(--gradient-green)" }}
              >
                <Car className="h-5 w-5" />
              </span>
              <span className="font-display text-sm font-bold">xanhSM · Cockpit</span>
            </Link>

            <div className="rounded-3xl border border-border/70 bg-card/80 p-7 shadow-[var(--shadow-card)] backdrop-blur-xl sm:p-9">
              <h2 className="font-display text-2xl font-bold tracking-tight">Chào mừng trở lại 👋</h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Đăng nhập để mở khoang lái điều hành chất lượng.
              </p>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <Field
                  icon={Mail}
                  type="email"
                  label="Email"
                  placeholder="ban@xanhsm.com"
                  value={email}
                  onChange={(v) => { setEmail(v); setAuthError(""); }}
                  required
                />
                <Field
                  icon={Lock}
                  type="password"
                  label="Mật khẩu"
                  placeholder="••••••••"
                  value={password}
                  onChange={(v) => { setPassword(v); setAuthError(""); }}
                  required
                />

                {authError && (
                  <div className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{authError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="group relative mt-2 flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl px-4 py-3 text-sm font-semibold text-white shadow-[var(--shadow-green)] transition hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60"
                  style={{ background: "var(--gradient-green)" }}
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      Đăng nhập
                      <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                    </>
                  )}
                </button>
              </form>

              <p className="mt-7 text-center text-sm text-muted-foreground">
                Tài khoản do quản trị viên cấp. Bạn là khách hàng?{" "}
                <a href={CUSTOMER_WEB_URL} className="font-semibold text-primary hover:underline">
                  Gửi phản hồi
                </a>
              </p>
            </div>

            <p className="mt-6 text-center">
              <Link to="/" className="font-mono text-xs text-muted-foreground hover:text-foreground">
                ← Về trang chủ
              </Link>
            </p>
          </div>
        </section>
      </div>

      <style>{`
        .auth-input {
          width: 100%;
          border-radius: 0.75rem;
          border: 1px solid var(--border);
          background: var(--card);
          padding: 0.7rem 0.875rem 0.7rem 2.5rem;
          font-size: 0.9rem;
          color: var(--foreground);
          outline: none;
          transition: box-shadow .15s, border-color .15s;
        }
        .auth-input::placeholder { color: var(--muted-foreground); }
        .auth-input:focus {
          border-color: var(--primary);
          box-shadow: 0 0 0 4px color-mix(in oklab, var(--primary) 18%, transparent);
        }
      `}</style>
    </main>
  );
}

function getAuthErrorMessage(error: { code?: string; message?: string }) {
  switch (error.code) {
    case "invalid_credentials":
      return "Email hoặc mật khẩu không đúng.";
    case "email_not_confirmed":
      return "Email chưa được xác nhận. Liên hệ quản trị viên để được hỗ trợ.";
    default:
      return error.message || "Đã có lỗi xảy ra";
  }
}

function Field({
  icon: Icon,
  type = "text",
  label,
  placeholder,
  value,
  onChange,
  required,
  minLength,
}: {
  icon: React.ComponentType<{ className?: string }>;
  type?: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  minLength?: number;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";
  const inputType = isPassword ? (showPassword ? "text" : "password") : type;

  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </label>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type={inputType}
          required={required}
          minLength={minLength}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="auth-input"
          style={isPassword ? { paddingRight: "2.5rem" } : undefined}
        />
        {isPassword && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPassword((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
      </div>
    </div>
  );
}

function PreviewStat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur">
      <div className="flex items-center gap-2 text-xs opacity-90">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-white/20">{icon}</span>
        {label}
      </div>
      <div className="mt-2 font-display text-2xl font-bold tracking-tight">{value}</div>
    </div>
  );
}
