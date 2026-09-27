import { useEffect, useRef } from "react";
import { Toaster } from "sonner";
import SubmitPage from "./pages/SubmitPage";
import StatusPage from "./pages/StatusPage";
import { navigate, usePath } from "./router";
import { Shell } from "./ui";

// /status, /status/, /status/CODE, /status/CODE/ — not /statuss or /status-faq.
export const STATUS_ROUTE = /^\/status(?:\/([^/]*))?\/?$/;

function decode(segment: string): string {
  try {
    return decodeURIComponent(segment).trim();
  } catch {
    return segment;
  }
}

export default function App() {
  const path = usePath();
  const status = STATUS_ROUTE.exec(path);
  const unknownPath = !status && path !== "/";

  // Two pages only; any other path is the form.
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

  return (
    <>
      <Shell>{status ? <StatusPage code={decode(status[1] ?? "")} /> : <SubmitPage />}</Shell>
      {/* Mounted once. The Staff web never mounted one, so its toasts were invisible. */}
      <Toaster position="top-center" richColors closeButton theme="system" />
    </>
  );
}
