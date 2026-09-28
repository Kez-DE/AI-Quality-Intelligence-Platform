// Optional Customer account pages (US-078): log in, sign up, forgot and reset
// password. Supabase Auth does the work; a new sign-up lands with role `guest`
// (a Customer account) through the database trigger, not through this code.
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { toast } from "sonner";
import { useAuth, useRecovery } from "../auth";
import { PASSWORD_CRITERIA, isStrongPassword, validatePassword } from "../password";
import { Link, navigate } from "../router";
import { authErrorText, redirectTo, supabase } from "../supabase";
import { Icon, Spinner } from "../ui";

function useTitle(title: string) {
  useEffect(() => {
    document.title = `${title} — AI-Quality`;
  }, [title]);
}

function AuthCard({ title, lead, children }: { title: string; lead?: ReactNode; children: ReactNode }) {
  useTitle(title);
  return (
    <>
      <h1 className="page-title">{title}</h1>
      {lead && <p className="mt-3 text-muted-foreground">{lead}</p>}
      {supabase ? (
        <div className="aurora-card surface mt-7 p-5 md:p-8">{children}</div>
      ) : (
        <p role="status" className="mt-7">
          Đăng nhập chưa được bật trên trang này. Bạn vẫn có thể{" "}
          <Link href="/" className="back-link">
            gửi phản hồi không cần tài khoản
          </Link>
          .
        </p>
      )}
    </>
  );
}

function FormError({ message }: { message: string }) {
  if (!message) return null;
  return (
    <p role="alert" className="field-error">
      <span className="sr-only">Lỗi: </span>
      {message}
    </p>
  );
}

function SubmitButton({ busy, children }: { busy: boolean; children: string }) {
  return (
    <button type="submit" className="btn btn-primary w-full" disabled={busy} aria-busy={busy}>
      {busy ? <Spinner /> : null}
      {children}
    </button>
  );
}

function EmailField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label htmlFor="auth-email" className="field-label">
        Email
      </label>
      <input
        id="auth-email"
        type="email"
        required
        autoComplete="email"
        inputMode="email"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="field-input mt-2"
      />
    </div>
  );
}

/** New password with the 5 criteria shown live, as on the Staff web. */
function NewPasswordField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const checks = validatePassword(value);
  return (
    <div>
      <label htmlFor="auth-new-password" className="field-label">
        Mật khẩu
      </label>
      <input
        id="auth-new-password"
        type="password"
        required
        autoComplete="new-password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-describedby="auth-password-criteria"
        className="field-input mt-2"
      />
      <ul id="auth-password-criteria" className="mt-3 grid gap-1.5 text-sm sm:grid-cols-2">
        {PASSWORD_CRITERIA.map((c) => (
          <li
            key={c.key}
            className={`flex items-center gap-2 ${checks[c.key] ? "text-foreground" : "text-muted-foreground"}`}
          >
            <span className={checks[c.key] ? "text-primary-strong" : "opacity-40"}>
              <Icon name={checks[c.key] ? "check" : "close"} className="size-4" />
            </span>
            {c.label}
            <span className="sr-only">{checks[c.key] ? ": đạt" : ": chưa đạt"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const WEAK_PASSWORD = "Mật khẩu chưa đáp ứng đủ 5 tiêu chí.";

/** Leave an auth page once logged in (also the landing after an OAuth return). */
function useLeaveWhenLoggedIn() {
  const auth = useAuth();
  const loggedIn = "email" in auth;
  useEffect(() => {
    if (loggedIn) navigate("/", { replace: true });
  }, [loggedIn]);
}

export function LoginPage() {
  useLeaveWhenLoggedIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    setBusy(false);
    if (error) setError(authErrorText(error));
  }

  async function oauth(provider: "google" | "facebook") {
    if (!supabase) return;
    const { error } = await supabase.auth.signInWithOAuth({ provider, options: { redirectTo: redirectTo("/") } });
    if (error) setError(authErrorText(error));
  }

  return (
    <AuthCard title="Đăng nhập" lead="Đăng nhập để xem lại các phản hồi bạn đã gửi. Không bắt buộc.">
      <div className="grid gap-2.5 sm:grid-cols-2">
        <button type="button" className="btn btn-secondary" onClick={() => void oauth("google")}>
          Tiếp tục với Google
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void oauth("facebook")}>
          Tiếp tục với Facebook
        </button>
      </div>
      <p className="my-6 text-center text-sm text-muted-foreground">hoặc dùng email</p>
      <form onSubmit={submit} className="space-y-5">
        <EmailField value={email} onChange={setEmail} />
        <div>
          <div className="flex items-baseline justify-between gap-3">
            <label htmlFor="auth-password" className="field-label">
              Mật khẩu
            </label>
            <Link href="/quen-mat-khau" className="back-link text-sm">
              Quên mật khẩu?
            </Link>
          </div>
          <input
            id="auth-password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="field-input mt-2"
          />
        </div>
        <FormError message={error} />
        <SubmitButton busy={busy}>Đăng nhập</SubmitButton>
      </form>
      <p className="mt-6 text-center">
        Chưa có tài khoản?{" "}
        <Link href="/dang-ky" className="back-link">
          Đăng ký
        </Link>
      </p>
    </AuthCard>
  );
}

export function SignupPage() {
  useLeaveWhenLoggedIn();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    if (!isStrongPassword(password)) {
      setError(WEAK_PASSWORD);
      return;
    }
    setBusy(true);
    setError("");
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: { data: { full_name: fullName.trim() }, emailRedirectTo: redirectTo("/") },
    });
    setBusy(false);
    if (error) setError(authErrorText(error));
    // With email confirmation on there is no session yet; the trigger has
    // already made the profile (role guest).
    else if (!data.session) setSent(true);
  }

  if (sent)
    return (
      <AuthCard title="Kiểm tra email">
        <p role="status">
          Chúng tôi đã gửi thư xác nhận tới <strong>{email.trim()}</strong>. Mở liên kết trong thư để hoàn tất đăng
          ký, rồi đăng nhập.
        </p>
      </AuthCard>
    );

  return (
    <AuthCard title="Tạo tài khoản" lead="Tài khoản giúp bạn xem lại phản hồi đã gửi. Gửi phản hồi vẫn không cần tài khoản.">
      <form onSubmit={submit} className="space-y-5">
        <div>
          <label htmlFor="auth-name" className="field-label">
            Họ và tên
          </label>
          <input
            id="auth-name"
            required
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="field-input mt-2"
          />
        </div>
        <EmailField value={email} onChange={setEmail} />
        <NewPasswordField value={password} onChange={setPassword} />
        <FormError message={error} />
        <SubmitButton busy={busy}>Đăng ký</SubmitButton>
      </form>
      <p className="mt-6 text-center">
        Đã có tài khoản?{" "}
        <Link href="/dang-nhap" className="back-link">
          Đăng nhập
        </Link>
      </p>
    </AuthCard>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: redirectTo("/dat-lai-mat-khau"),
    });
    setBusy(false);
    if (error) setError(authErrorText(error));
    else setSent(true);
  }

  return (
    <AuthCard title="Quên mật khẩu" lead="Nhập email của tài khoản. Chúng tôi sẽ gửi liên kết đặt lại mật khẩu.">
      {sent ? (
        // Same answer whether or not the email has an account.
        <p role="status">Nếu email này có tài khoản, thư đặt lại mật khẩu đã được gửi. Hãy kiểm tra hộp thư.</p>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <EmailField value={email} onChange={setEmail} />
          <FormError message={error} />
          <SubmitButton busy={busy}>Gửi liên kết</SubmitButton>
        </form>
      )}
      <p className="mt-6">
        <Link href="/dang-nhap" className="back-link">
          <Icon name="arrowLeft" className="size-4" />
          Quay lại đăng nhập
        </Link>
      </p>
    </AuthCard>
  );
}

export function ResetPasswordPage() {
  const auth = useAuth();
  const recovery = useRecovery();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    if (!isStrongPassword(password)) {
      setError(WEAK_PASSWORD);
      return;
    }
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) return setError(authErrorText(error));
    toast.success("Đã đổi mật khẩu");
    navigate("/");
  }

  // Only the session the recovery link opened gets the form. An expired or used
  // link keeps any existing login (auth-js), and that login must not be able to
  // set a new password here without the old one.
  let body: ReactNode;
  if (auth.kind === "loading") body = <Spinner />;
  else if (!recovery)
    body = (
      <p role="status">
        Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.{" "}
        <Link href="/quen-mat-khau" className="back-link">
          Gửi liên kết mới
        </Link>
      </p>
    );
  else
    body = (
      <form onSubmit={submit} className="space-y-5">
        <NewPasswordField value={password} onChange={setPassword} />
        <FormError message={error} />
        <SubmitButton busy={busy}>Lưu mật khẩu mới</SubmitButton>
      </form>
    );

  return <AuthCard title="Đặt lại mật khẩu">{body}</AuthCard>;
}
