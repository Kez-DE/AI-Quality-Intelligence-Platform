import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Car, Loader2, Mail, Lock, User, ArrowRight, CircleCheck } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Đăng nhập · AI Quality Intelligence" },
      { name: "description", content: "Đăng nhập vào Quality Operation Cockpit của xanhSM." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirmationEmail, setConfirmationEmail] = useState("");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) navigate({ to: "/dashboard" });
    });
  }, [navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
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
          navigate({ to: "/dashboard" });
          return;
        }
        setConfirmationEmail(email);
        toast.success("Đăng ký thành công! Hãy xác nhận email để đăng nhập.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        toast.success("Đăng nhập thành công");
        navigate({ to: "/dashboard" });
      }
    } catch (err: any) {
      toast.error(getAuthErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left brand panel */}
      <div
        className="hidden lg:flex flex-col justify-between p-10 text-white relative overflow-hidden"
        style={{ background: "var(--gradient-hero)" }}
      >
        <div className="flex items-center gap-2 relative z-10">
          <div className="h-10 w-10 rounded-xl bg-white/15 grid place-items-center backdrop-blur">
            <Car className="h-5 w-5" />
          </div>
          <div>
            <div className="font-display font-bold">xanhSM</div>
            <div className="text-[11px] opacity-80 font-mono">Quality Operation Cockpit</div>
          </div>
        </div>
        <div className="relative z-10">
          <h1 className="font-display text-4xl font-bold leading-tight">
            Biến hàng nghìn phản hồi mỗi ngày thành{" "}
            <span className="opacity-90">hành động vận hành</span>.
          </h1>
          <p className="mt-4 opacity-90 max-w-md">
            AI Quality Intelligence Platform — phát hiện sớm sự cố chất lượng dịch vụ smart mobility
            trước khi chúng thành khủng hoảng.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {["Real-time", "Alert · SLA", "Human-in-the-loop", "AI Chat"].map((k) => (
              <span
                key={k}
                className="text-xs font-mono px-2.5 py-1 rounded-md bg-white/15 border border-white/25"
              >
                {k}
              </span>
            ))}
          </div>
        </div>
        <div className="text-[11px] font-mono opacity-70 relative z-10">
          © xanhSM · Smart Mobility Feedback Analytics
        </div>
        {/* decorative blobs */}
        <div className="absolute -bottom-20 -right-20 h-80 w-80 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute top-1/3 -left-20 h-60 w-60 rounded-full bg-xanh-cyan/30 blur-3xl" />
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-2 mb-6">
            <div
              className="h-9 w-9 rounded-xl grid place-items-center text-white"
              style={{ background: "var(--gradient-green)" }}
            >
              <Car className="h-5 w-5" />
            </div>
            <div className="font-display font-bold">xanhSM Cockpit</div>
          </div>

          <h2 className="font-display text-3xl font-bold">
            {mode === "signin" ? "Đăng nhập" : "Tạo tài khoản"}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {mode === "signin"
              ? "Truy cập khoang lái điều hành chất lượng dịch vụ."
              : "Đăng ký để bắt đầu thu thập & phân tích phản hồi."}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {confirmationEmail && (
              <div className="rounded-xl border border-xanh-green/30 bg-xanh-mint p-4 text-sm text-xanh-deep">
                <div className="flex items-center gap-2 font-semibold">
                  <CircleCheck className="h-4 w-4" />
                  Kiểm tra email để hoàn tất đăng ký
                </div>
                <p className="mt-1 text-xs leading-relaxed">
                  Supabase đã gửi liên kết xác nhận tới {confirmationEmail}. Sau khi xác nhận, quay
                  lại đây để đăng nhập.
                </p>
              </div>
            )}
            {mode === "signup" && (
              <Field icon={User} placeholder="Họ và tên" value={fullName} onChange={setFullName} />
            )}
            <Field
              icon={Mail}
              type="email"
              placeholder="Email"
              value={email}
              onChange={setEmail}
              required
            />
            <Field
              icon={Lock}
              type="password"
              placeholder="Mật khẩu mạnh (tối thiểu 8 ký tự)"
              value={password}
              onChange={setPassword}
              required
              minLength={8}
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 rounded-xl text-white font-semibold flex items-center justify-center gap-2 shadow-[var(--shadow-green)] transition-transform hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60"
              style={{ background: "var(--gradient-green)" }}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  {mode === "signin" ? "Đăng nhập" : "Đăng ký"}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-sm text-center text-muted-foreground">
            {mode === "signin" ? (
              <>
                Chưa có tài khoản?{" "}
                <button
                  onClick={() => {
                    setMode("signup");
                    setConfirmationEmail("");
                  }}
                  className="text-xanh-deep font-semibold hover:underline"
                >
                  Đăng ký
                </button>
              </>
            ) : (
              <>
                Đã có tài khoản?{" "}
                <button
                  onClick={() => setMode("signin")}
                  className="text-xanh-deep font-semibold hover:underline"
                >
                  Đăng nhập
                </button>
              </>
            )}
          </div>

          <div className="mt-8 text-center">
            <Link to="/" className="text-xs font-mono text-muted-foreground hover:text-foreground">
              ← Về trang chủ
            </Link>
          </div>
        </div>
      </div>
    </div>
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
  placeholder,
  value,
  onChange,
  required,
  minLength,
}: {
  icon: React.ComponentType<{ className?: string }>;
  type?: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  minLength?: number;
}) {
  return (
    <label className="relative block">
      <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <input
        type={type}
        required={required}
        minLength={minLength}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-11 pl-10 pr-3 rounded-xl border border-border bg-white focus:outline-none focus:ring-2 focus:ring-xanh-green/40 focus:border-xanh-green/40 transition-all"
      />
    </label>
  );
}
