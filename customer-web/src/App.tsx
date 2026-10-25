import { useEffect, useRef } from "react";
import { Toaster } from "sonner";
import ChatWidget from "./ChatWidget";
import { AuthProvider } from "./auth";
import { ForgotPasswordPage, LoginPage, ResetPasswordPage, SignupPage } from "./pages/AuthPages";
import MyFeedbackPage from "./pages/MyFeedbackPage";
import SubmitPage from "./pages/SubmitPage";
import StatusPage from "./pages/StatusPage";
import { navigate, usePath } from "./router";
import { Shell } from "./ui";

// /status, /status/, /status/CODE, /status/CODE/ — not /statuss or /status-faq.
export const STATUS_ROUTE = /^\/status(?:\/([^/]*))?\/?$/;

// Customer account pages (US-078). A trailing slash is allowed, nothing else.
const PAGES = {
  "/": SubmitPage,
  "/dang-nhap": LoginPage,
  "/dang-ky": SignupPage,
  "/quen-mat-khau": ForgotPasswordPage,
  "/dat-lai-mat-khau": ResetPasswordPage,
  "/cua-toi": MyFeedbackPage,
} as const;

export type Route = { page: keyof typeof PAGES } | { page: "status"; code: string } | null;

/** The page for a path, or null for an unknown path (redirected to `/`). */
export function matchRoute(path: string): Route {
  const status = STATUS_ROUTE.exec(path);
  if (status) return { page: "status", code: decode(status[1] ?? "") };
  const bare = path.length > 1 ? path.replace(/\/$/, "") : path;
  return bare in PAGES ? { page: bare as keyof typeof PAGES } : null;
}

function decode(segment: string): string {
  try {
    return decodeURIComponent(segment).trim();
  } catch {
    return segment;
  }
}

export default function App() {
  const path = usePath();
  const route = matchRoute(path);
  const unknownPath = route === null;

  // Any other path is the form.
  useEffect(() => {
    if (unknownPath) navigate("/", { replace: true });
  }, [unknownPath]);

  // A route change swaps the whole page and drops focus to <body>. Move it to
  // the new page heading so keyboard and screen-reader users land on it. Not on
  // first load: the browser already starts at the top of a fresh document.
  // Compare paths rather than counting renders: StrictMode runs effects twice.
  const lastPath = useRef(path);
  useEffect(() => {
    if (lastPath.current === path) return;
    lastPath.current = path;
    const heading = document.querySelector<HTMLElement>("h1");
    if (!heading) return;
    heading.tabIndex = -1;
    heading.focus();
  }, [path]);

  const Page = route && route.page !== "status" ? PAGES[route.page] : SubmitPage;

  return (
    <AuthProvider>
      <Shell>{route?.page === "status" ? <StatusPage code={route.code} /> : <Page />}</Shell>
      <ChatWidget />
      {/* Mounted once. The Staff web never mounted one, so its toasts were invisible. */}
      <Toaster position="top-center" richColors closeButton theme="system" />
    </AuthProvider>
  );
}
