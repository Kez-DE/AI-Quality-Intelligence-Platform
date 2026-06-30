import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import {
  Car,
  Loader2,
  Mail,
  Lock,
  User,
  ArrowRight,
  AlertCircle,
  CircleCheck,
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

function AuthPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirmationEmail, setConfirmationEmail] = useState("");
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) window.location.replace("/dashboard");
    });
  }, []);

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
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: window.location.origin + "/dashboard",
            data: { full_name: fullName || email.split("@")[0] },
          },
        });
        if (error) throw error;
        if (data.session) {
          toast.success("Đăng ký thành công");
          window.location.assign("/dashboard");
          return;
        }
        setConfirmationEmail(email);
        toast.success("Đăng ký thành công! Hãy xác nhận email để đăng nhập.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        await supabase.auth.getSession();
        toast.success("Đăng nhập thành công");
        window.location.assign("/dashboard");
      }
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
              {/* Tabs */}
              <div className="mb-7 grid grid-cols-2 rounded-xl bg-muted p-1 text-sm">
                {(
                  [
                    ["signin", "Đăng nhập"],
                    ["signup", "Tạo tài khoản"],
                  ] as const
                ).map(([m, lbl]) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => {
                      setMode(m);
                      setConfirmationEmail("");
                      setAuthError("");
                    }}
                    className={`rounded-lg px-3 py-2 font-medium transition ${
                      mode === m
                        ? "bg-card text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {lbl}
                  </button>
                ))}
              </div>

              <h2 className="font-display text-2xl font-bold tracking-tight">
                {mode === "signin" ? "Chào mừng trở lại 👋" : "Tạo tài khoản"}
              </h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                {mode === "signin"
                  ? "Đăng nhập để mở khoang lái điều hành chất lượng."
                  : "Đăng ký để bắt đầu thu thập & phân tích phản hồi."}
              </p>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                {confirmationEmail && (
                  <div className="rounded-xl border border-success/30 bg-success/10 p-4 text-sm text-foreground">
                    <div className="flex items-center gap-2 font-semibold">
                      <CircleCheck className="h-4 w-4 text-success" />
                      Kiểm tra email để hoàn tất đăng ký
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                      Supabase đã gửi liên kết xác nhận tới {confirmationEmail}. Sau khi xác nhận,
                      quay lại đây để đăng nhập.
                    </p>
                  </div>
                )}

                {mode === "signup" && (
                  <Field
                    icon={User}
                    label="Họ và tên"
                    placeholder="Nguyễn Văn A"
                    value={fullName}
                    onChange={setFullName}
                  />
                )}
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
                  placeholder={mode === "signin" ? "••••••••" : "Tối thiểu 8 ký tự"}
                  value={password}
                  onChange={(v) => { setPassword(v); setAuthError(""); }}
                  required
                />
                {mode === "signup" && <PasswordStrengthHint password={password} />}

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
                      {mode === "signin" ? "Đăng nhập" : "Đăng ký"}
                      <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                    </>
                  )}
                </button>

                <div className="relative flex items-center gap-3 py-1">
                  <hr className="flex-1 border-border/60" />
                  <span className="text-xs text-muted-foreground">hoặc</span>
                  <hr className="flex-1 border-border/60" />
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() =>
                      supabase.auth.signInWithOAuth({
                        provider: "google",
                        options: { redirectTo: window.location.origin + "/dashboard" },
                      })
                    }
                    className="flex items-center justify-center gap-2.5 rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium transition hover:bg-muted"
                  >
                    <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden>
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                    Google
                  </button>
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
                      <path fill="#1877F2" d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.236 2.686.236v2.97h-1.514c-1.491 0-1.956.93-1.956 1.886v2.267h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z" />
                    </svg>
                    Facebook
                  </button>
                </div>
              </form>

              <p className="mt-7 text-center text-sm text-muted-foreground">
                {mode === "signin" ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
                <button
                  onClick={() => {
                    setMode(mode === "signin" ? "signup" : "signin");
                    setConfirmationEmail("");
                    setAuthError("");
                  }}
                  className="font-semibold text-primary hover:underline"
                >
                  {mode === "signin" ? "Tạo tài khoản" : "Đăng nhập"}
                </button>
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
    case "weak_password":
      return "Mật khẩu quá yếu hoặc đã xuất hiện trong dữ liệu rò rỉ. Hãy dùng ít nhất 8 ký tự gồm chữ hoa, chữ thường, số và ký tự đặc biệt.";
    case "invalid_credentials":
      return "Email hoặc mật khẩu không đúng. Nếu vừa đăng ký, hãy xác nhận email trước.";
    case "email_not_confirmed":
      return "Email chưa được xác nhận. Hãy mở email Supabase đã gửi rồi thử lại.";
    case "user_already_exists":
      return "Email này đã được đăng ký. Hãy chuyển sang đăng nhập.";
    case "over_email_send_rate_limit":
      return "Đã gửi quá nhiều email xác nhận. Vui lòng chờ vài phút rồi thử lại.";
    default:
      return error.message ?? "Đã có lỗi xảy ra";
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

export function validatePassword(pw: string) {
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
