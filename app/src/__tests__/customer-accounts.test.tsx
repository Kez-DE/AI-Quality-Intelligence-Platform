// US-078: Customer accounts (role guest) must never look like, or be one click
// from, a Staff account in the Staff web (decision 0018).
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { describe, it, expect, vi } from "vitest";

const { users } = vi.hoisted(() => {
  const at = "2026-09-01T00:00:00Z";
  return {
    users: [
      {
        id: "a1",
        email: "admin@x.vn",
        full_name: "Admin",
        role: "admin",
        department: null,
        created_at: at,
      },
      {
        id: "s1",
        email: "staff@x.vn",
        full_name: "Staff",
        role: "staff",
        department: "IT",
        created_at: at,
      },
      {
        id: "p1",
        email: "pending@x.vn",
        full_name: "Pending",
        role: "pending",
        department: null,
        created_at: at,
      },
      {
        id: "g1",
        email: "khach@x.vn",
        full_name: "Khach",
        role: "guest",
        department: null,
        created_at: at,
      },
    ],
  };
});

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (options: unknown) => ({ options }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    apiFetch: vi.fn(async (path: string) => ({ data: path === "/api/users" ? users : [] })),
    useMe: () => ({
      isLoading: false,
      data: { id: "a1", email: "admin@x.vn", role: "admin", department: null },
    }),
  };
});

import { Route } from "@/routes/_authenticated/admin";
import EmployeesPanel from "@/components/EmployeesPanel";

function withQuery(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const rowOf = (el: HTMLElement) => el.closest(".grid") as HTMLElement;

describe("admin user list", () => {
  it("shows a Customer account read-only: no role or department select", async () => {
    const AdminPage = (Route as unknown as { options: { component: () => ReactNode } }).options
      .component;
    withQuery(<AdminPage />);
    fireEvent.change(await screen.findByPlaceholderText(/Tìm người dùng/), {
      target: { value: "@x.vn" },
    });

    const guestRow = rowOf(await screen.findByText("khach@x.vn"));
    expect(within(guestRow).queryAllByRole("combobox")).toHaveLength(0);
    expect(within(guestRow).getByText("Khách hàng")).toBeInTheDocument();

    const staffRow = rowOf(screen.getByText("staff@x.vn"));
    expect(within(staffRow).getAllByRole("combobox")).toHaveLength(2);
  });
});

describe("EmployeesPanel", () => {
  it("lists Staff accounts only, never Customer or Pending accounts", async () => {
    withQuery(
      <EmployeesPanel me={{ id: "a1", email: "admin@x.vn", role: "admin", department: null }} />,
    );
    expect(await screen.findByText("staff@x.vn")).toBeInTheDocument();
    expect(screen.getByText("admin@x.vn")).toBeInTheDocument();
    expect(screen.queryByText("khach@x.vn")).toBeNull();
    expect(screen.queryByText("pending@x.vn")).toBeNull();
  });
});
