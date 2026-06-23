// Helper gọi backend FastAPI kèm Supabase Bearer token + hook đọc role (RBAC).
//
// Backend dùng SERVICE_ROLE_KEY (bypass RLS) nên định danh/quyền được kiểm ở tầng API.
// Mọi request admin/ops PHẢI gắn Authorization: Bearer <access_token>.
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

export const API_BASE = import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000";

export type Role = "admin" | "manager" | "staff" | "guest";

export type Department = "IT" | "CSKH" | "Vận hành" | "Marketing" | null;

/** 4 phòng ban — khớp backend TEAMS / profiles.department. */
export const ALL_TEAMS = ["IT", "CSKH", "Vận hành", "Marketing"] as const;

export type Me = {
  id: string;
  email: string | null;
  role: Role;
  department: Department;
};

/** Danh sách phòng ban user được phép xem.
 *  - admin: cả 4 phòng.
 *  - ops đã gán phòng: chỉ phòng của mình.
 *  - ops chưa gán phòng: rỗng (không thấy gì → render thông báo liên hệ admin). */
export function visibleTeams(me: Me | null | undefined): string[] {
  if (!me) return [];
  if (me.role === "admin") return [...ALL_TEAMS];
  return me.department ? [me.department] : [];
}

/** ops user (manager/staff) chưa được gán phòng ban → không có quyền xem dữ liệu phòng nào. */
export function isUnassignedOps(me: Me | null | undefined): boolean {
  return !!me && me.role !== "admin" && !me.department;
}

/** Lấy access_token hiện tại từ Supabase session. */
async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

/** fetch tới backend, tự gắn Bearer token. Ném Error với message từ `detail` nếu lỗi. */
export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // body không phải JSON — giữ status text.
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

/** Đọc danh tính + role của user đang đăng nhập. Dùng để render nav/route theo quyền. */
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const json = await apiFetch<{ data: Me }>("/api/me");
      return json.data;
    },
    staleTime: 60_000,
    retry: false,
  });
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Quản trị viên",
  manager: "Quản lý",
  staff: "Nhân viên",
  guest: "Khách",
};
