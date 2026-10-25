// Who is on the page (US-078). A Supabase session alone is not a Customer
// account: the role comes from the backend's /api/me, and only role `guest`
// may call /api/customer/*. Any other role (staff, pending, ...) is told to use
// the Staff web and gets no customer API calls.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";
import { ApiError, getMe } from "./api";
import { authCallback, authErrorText, supabase } from "./supabase";

export type Auth =
  | { kind: "anon" }
  | { kind: "loading" }
  | { kind: "checking"; email: string }
  | { kind: "customer"; email: string; token: string; userId: string }
  | { kind: "staff"; email: string }
  | { kind: "error"; email: string; retry: () => void };

export const STAFF_MESSAGE = "Tài khoản nhân viên dùng Staff web";

export const AuthContext = createContext<Auth>({ kind: "anon" });

// True only for the session a password-recovery link opened.
const RecoveryContext = createContext(false);

/** Not yet known whether this is a Customer account. */
export function settling(auth: Auth): boolean {
  return auth.kind === "loading" || auth.kind === "checking";
}

export function useAuth(): Auth {
  return useContext(AuthContext);
}

export function useRecovery(): boolean {
  return useContext(RecoveryContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  // Until getSession settles (it also reads a recovery or OAuth token from the URL).
  const [loading, setLoading] = useState(!!supabase);
  const [role, setRole] = useState<{ userId: string; role: string | null } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [recoveryUser, setRecoveryUser] = useState<string | null>(null);

  useEffect(() => {
    if (!supabase) return;
    // A failed OAuth, confirmation or reset link lands here logged out; say why.
    if (authCallback.error) {
      toast.error(authErrorText({ code: authCallback.error }), { duration: 8000 });
      authCallback.error = null; // once, also under StrictMode
      window.history.replaceState(null, "", window.location.pathname);
    }
    void supabase.auth
      .getSession()
      .then(({ data }) => {
        setSession(data.session);
        // PASSWORD_RECOVERY may fire before we subscribe; the link's token is the fallback.
        if (data.session && data.session.access_token === authCallback.recoveryToken)
          setRecoveryUser(data.session.user.id);
      })
      .finally(() => setLoading(false));
    // No awaiting Supabase calls inside this callback (supabase-js can deadlock).
    const { data } = supabase.auth.onAuthStateChange((event, next) => {
      setSession(next);
      if (event === "PASSWORD_RECOVERY") setRecoveryUser(next?.user.id ?? null);
      else if (event === "SIGNED_OUT" || event === "USER_UPDATED") setRecoveryUser(null);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  // Look the role up once per user (or retry), not on every token refresh.
  const userId = session?.user.id;
  const token = session?.access_token;
  useEffect(() => {
    if (!userId || !token) return;
    let current = true;
    getMe(token).then(
      (me) => current && setRole({ userId, role: me.role }),
      (err: unknown) => {
        if (!current) return;
        // customerFetch sent a fresh token, so a 401 means the account or the
        // session is gone. Drop the local session instead of staying in "error".
        if (err instanceof ApiError && err.status === 401) void supabase?.auth.signOut({ scope: "local" });
        else setRole({ userId, role: null });
      },
    );
    return () => {
      current = false;
    };
  }, [userId, attempt]); // not `token`: a refreshed token keeps the same role

  let auth: Auth = loading ? { kind: "loading" } : { kind: "anon" };
  if (session && token) {
    const email = session.user.email ?? "";
    const retry = () => {
      setRole(null); // back to "checking" while it runs
      setAttempt((n) => n + 1);
    };
    if (role?.userId !== session.user.id) auth = { kind: "checking", email };
    else if (role.role === "guest") auth = { kind: "customer", email, token, userId: session.user.id };
    else if (role.role === null) auth = { kind: "error", email, retry };
    else auth = { kind: "staff", email };
  }

  return (
    <AuthContext.Provider value={auth}>
      <RecoveryContext.Provider value={!!session && session.user.id === recoveryUser}>
        {children}
      </RecoveryContext.Provider>
    </AuthContext.Provider>
  );
}

export async function signOut() {
  await supabase?.auth.signOut();
}
