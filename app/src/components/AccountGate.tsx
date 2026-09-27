// Full-page screens the `_authenticated` layout shows instead of AppShell when
// `staffWebGate` does not allow the cockpit (US-077). Neither renders nav or
// fetches backend data.
import { useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { AlertCircle, Car, Clock, KeyRound, Loader2, LogOut } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { apiFetch } from "@/lib/api";
import { isStrongPassword } from "@/lib/password";
import { PasswordStrengthHint } from "@/components/PasswordStrengthHint";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function useSignOut() {
  const router = useRouter();
  return async () => {
    await supabase.auth.signOut();
    toast.success("Đã đăng xuất");
    router.navigate({ to: "/auth", replace: true });
  };
}

function GateFrame({ children }: { children: React.ReactNode }) {
  return (
    <main className="relative grid min-h-screen place-items-center px-4 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: "var(--gradient-mesh)" }}
      />
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl text-white shadow-[var(--shadow-green)]"
            style={{ background: "var(--gradient-green)" }}
          >
            <Car className="h-5 w-5" />
          </span>
          <span className="font-display text-sm font-bold">xanhSM · Cockpit</span>
        </div>
        <div className="rounded-3xl border border-border/70 bg-card/80 p-7 shadow-[var(--shadow-card)] backdrop-blur-xl sm:p-9">
          {children}
        </div>
      </div>
    </main>
  );
}

/** First login of an admin-created account: replace the temporary password. */
export function ChangePasswordScreen() {
  const router = useRouter();
  const signOut = useSignOut();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!isStrongPassword(password)) {
      setError("Mật khẩu chưa đủ mạnh. Hãy đáp ứng tất cả 5 tiêu chí.");
      return;
    }
    if (password !== confirm) {
      setError("Hai mật khẩu không khớp.");
      return;
    }
    setSaving(true);
    try {
      // The flag is in app_metadata, which only the backend can clear.
      await apiFetch("/api/me/password", {
        method: "POST",
        body: JSON.stringify({ new_password: password }),
      });
      // New JWT without the flag, so RLS (is_ops_staff) lets the account in too.
      await supabase.auth.refreshSession();
      toast.success("Đã đổi mật khẩu");
      // Re-run the layout guard: it now reads must_change_password = false.
      await router.invalidate();
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : "Không đổi được mật khẩu");
    } finally {
      setSaving(false);
    }
  }

  return (
    <GateFrame>
      <KeyRound className="h-8 w-8 text-xanh-green" />
      <h1 className="mt-3 font-display text-2xl font-bold tracking-tight">Đổi mật khẩu</h1>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Tài khoản của bạn đang dùng mật khẩu tạm do quản trị viên cấp. Hãy đặt mật khẩu mới để tiếp
        tục.
      </p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="new-password">Mật khẩu mới</Label>
          <Input
            id="new-password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setError("");
            }}
          />
        </div>
        <PasswordStrengthHint password={password} />
        <div className="space-y-1.5">
          <Label htmlFor="confirm-password">Nhập lại mật khẩu mới</Label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => {
              setConfirm(e.target.value);
              setError("");
            }}
          />
        </div>
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <button
          type="submit"
          disabled={saving}
          className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white shadow-[var(--shadow-green)] disabled:opacity-60"
          style={{ background: "var(--gradient-green)" }}
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Lưu mật khẩu mới"}
        </button>
      </form>
      <button
        type="button"
        onClick={signOut}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        <LogOut className="h-4 w-4" />
        Đăng xuất
      </button>
    </GateFrame>
  );
}

/** Pending account: logged in, but no Staff role yet. */
export function PendingAccountScreen({ email }: { email?: string | null }) {
  const signOut = useSignOut();
  return (
    <GateFrame>
      <Clock className="h-8 w-8 text-xanh-amber" />
      <h1 className="mt-3 font-display text-2xl font-bold tracking-tight">
        Tài khoản đang chờ admin cấp quyền
      </h1>
      <p className="mt-1.5 text-sm text-muted-foreground">
        {email ? (
          <>
            Tài khoản <span className="font-mono text-foreground">{email}</span> chưa được cấp quyền
            truy cập.
          </>
        ) : (
          "Tài khoản của bạn chưa được cấp quyền truy cập."
        )}{" "}
        Khi quản trị viên cấp quyền, hãy tải lại trang hoặc đăng nhập lại.
      </p>
      <button
        type="button"
        onClick={signOut}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium hover:bg-muted"
      >
        <LogOut className="h-4 w-4" />
        Đăng xuất
      </button>
    </GateFrame>
  );
}
