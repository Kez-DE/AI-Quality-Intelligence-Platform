// Shared pieces for the Customer web pages: the page frame, the lookup box,
// the grouped Lookup code, and a small authored icon set (one stroke weight).
import { useState, type ReactNode } from "react";
import { STAFF_MESSAGE, signOut, useAuth } from "./auth";
import { Link, navigate, statusPath } from "./router";
import { supabase } from "./supabase";

const ICONS = {
  check: <path d="M20 6 9 17l-5-5" />,
  copy: (
    <>
      <rect x="9" y="9" width="12" height="12" rx="2.5" />
      <path d="M5 15V6a2 2 0 0 1 2-2h9" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 20.5a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  mask: (
    <>
      <path d="M3 3l18 18" />
      <path d="M10.6 5.2A9.8 9.8 0 0 1 12 5c5 0 8.9 4.3 10 7a12.6 12.6 0 0 1-2.4 3.4" />
      <path d="M6.5 6.6C4.3 8 2.7 10.2 2 12c1.1 2.7 5 7 10 7a9.6 9.6 0 0 0 4.6-1.2" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 12a8 8 0 1 1-2.3-5.7L20 8.5" />
      <path d="M20 3.5v5h-5" />
    </>
  ),
  arrowRight: (
    <>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </>
  ),
  arrowLeft: (
    <>
      <path d="M19 12H5" />
      <path d="m11 6-6 6 6 6" />
    </>
  ),
  chat: <path d="M20 14.5a2 2 0 0 1-2 2H8.5L4 20V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2Z" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  send: (
    <>
      <path d="M21 3 10 14" />
      <path d="m21 3-7 18-4-7-7-4Z" />
    </>
  ),
  logout: (
    <>
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
      <path d="M10 17l-5-5 5-5M5 12h10" />
    </>
  ),
} as const;

export function Icon({ name, className = "size-5" }: { name: keyof typeof ICONS; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {ICONS[name]}
    </svg>
  );
}

/** Filled "!" disc for warning text; reads at small sizes where a stroke icon blurs. */
export function WarningMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-6 shrink-0" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="12" fill="currentColor" />
      <path d="M12 6.5v7" stroke="var(--card)" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="12" cy="17.4" r="1.5" fill="var(--card)" />
    </svg>
  );
}

export function Spinner() {
  return (
    <svg viewBox="0 0 24 24" className="size-5 animate-spin" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/** The Lookup code in groups of four. Groups are spaced with CSS, not spaces,
 *  so a manual text selection still copies the exact code. */
export function CodeText({ code, className = "" }: { code: string; className?: string }) {
  const groups = code.match(/.{1,4}/g) ?? [code];
  return (
    <span className={`code-text ${className}`}>
      <span className="sr-only">{code}</span>
      <span aria-hidden="true">
        {groups.map((g, i) => (
          <span key={i}>{g}</span>
        ))}
      </span>
    </span>
  );
}

export function LookupForm({ initial = "", id = "lookup-code" }: { initial?: string; id?: string }) {
  const [value, setValue] = useState(initial);
  // People retype a grouped code with spaces; the code itself never has any.
  const code = value.replace(/\s+/g, "");

  return (
    <form
      role="search"
      className="mt-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (code) navigate(statusPath(code));
      }}
    >
      <label htmlFor={id} className="field-label">
        Mã tra cứu
      </label>
      <p id={`${id}-hint`} className="field-hint">
        Mã gồm 12 ký tự, phân biệt chữ hoa và chữ thường.
      </p>
      <div className="mt-2 flex gap-2">
        <input
          id={id}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-describedby={`${id}-hint`}
          className="field-input min-w-0 flex-1 font-mono tracking-wide"
          autoComplete="off"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="search"
        />
        <button type="submit" className="btn btn-secondary shrink-0" disabled={!code}>
          <Icon name="search" />
          Tra cứu
        </button>
      </div>
    </form>
  );
}

function AccountNav() {
  const auth = useAuth();
  if (!supabase) return <span className="text-sm font-medium text-on-band-muted">Phản hồi khách hàng</span>;
  if (auth.kind === "loading") return null;
  if (auth.kind === "anon")
    return (
      <Link href="/dang-nhap" className="btn btn-on-band">
        Đăng nhập
      </Link>
    );
  return (
    <button
      type="button"
      className="btn btn-on-band"
      onClick={() => void signOut().then(() => navigate("/"))}
    >
      <Icon name="logout" className="size-4" />
      Đăng xuất
    </button>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="band">
        <div className="mx-auto flex h-16 w-full max-w-2xl items-center justify-between gap-4 px-4">
          <Link href="/" className="wordmark" aria-label="AI-Quality, về trang gửi phản hồi">
            AI-<span>Quality</span>
          </Link>
          <AccountNav />
        </div>
        {"email" in auth && (
          <nav aria-label="Tài khoản" className="mx-auto flex w-full max-w-2xl items-center justify-between gap-3 px-4 pb-3 text-sm">
            <span className="min-w-0 truncate text-on-band-muted" title={auth.email}>
              {auth.email}
            </span>
            <Link href="/cua-toi" className="shrink-0 font-semibold text-on-band underline">
              Phản hồi của tôi
            </Link>
          </nav>
        )}
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-16 pt-8 md:pt-12">
        {/* A staff or pending login: no customer API calls anywhere (US-078). */}
        {auth.kind === "staff" && (
          <p role="status" className="notice mb-8">
            <strong>{STAFF_MESSAGE}.</strong> Trang này dành cho khách hàng; bạn vẫn có thể gửi phản hồi
            không kèm tài khoản.
          </p>
        )}
        {/* /api/me failed: until a retry works, the form posts without the account. */}
        {auth.kind === "error" && (
          <p role="alert" className="notice mb-8">
            <strong>Không kiểm tra được tài khoản.</strong> Phản hồi gửi lúc này sẽ không được lưu vào tài
            khoản.{" "}
            <button type="button" className="back-link" onClick={auth.retry}>
              Thử lại
            </button>
          </p>
        )}
        {children}
      </main>
      <footer className="border-t border-border">
        <p className="mx-auto max-w-2xl px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-6 text-sm text-muted-foreground">
          AI-Quality · Gửi phản hồi không cần tài khoản
        </p>
      </footer>
    </div>
  );
}
