// Staff web access gate (US-077, US-078). Pure so the decision is unit-tested; the
// `_authenticated` layout feeds it the profile role and the auth user metadata.
import type { Role, StaffRole } from "@/lib/api";

const STAFF_ROLES: readonly StaffRole[] = ["admin", "manager", "staff"];

// Path prefixes each Staff role may not open (matched with startsWith, so
// sub-routes are blocked too). The backend enforces the same rules per endpoint.
const BLOCKED_PREFIXES: Record<StaffRole, readonly string[]> = {
  admin: [],
  manager: ["/admin"],
  staff: ["/admin", "/insights", "/reports", "/completion-reports"],
};

export function isStaffRole(value: unknown): value is StaffRole {
  return STAFF_ROLES.includes(value as StaffRole);
}

/** Staff roles and `guest` (Customer account, US-078) pass through. Fail closed:
 *  anything else (pending, null after a failed profile read, a typo) is Pending. */
export function toRole(value: unknown): Role {
  if (value === "guest") return "guest";
  return isStaffRole(value) ? value : "pending";
}

export type Gate =
  | "change-password" // admin-created account still on its temporary password
  | "pending" // no Staff role yet: only the waiting screen
  | "customer" // Customer account (role guest): pointed to the Customer web
  | "to-dashboard" // Staff role, but not for this path
  | "allow";

export function staffWebGate(input: {
  role: unknown;
  mustChangePassword: boolean;
  pathname: string;
}): Gate {
  // Replace the temporary password before anything else, whatever the role.
  if (input.mustChangePassword) return "change-password";
  const role = toRole(input.role);
  if (role === "pending") return "pending";
  if (role === "guest") return "customer";
  if (BLOCKED_PREFIXES[role].some((p) => input.pathname.startsWith(p))) return "to-dashboard";
  return "allow";
}
