"""RBAC boundary matrix using the audit user, flipping roles via service key."""
import os, json, urllib.request
from pathlib import Path

for line in Path(__file__).resolve().parents[2].joinpath(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
svc = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
anon = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_PUBLISHABLE_KEY"])
EMAIL, PW = "audit-e2e-20260711@example.com", "Audit-E2E-20260711!x"
UID = json.load(open(Path(__file__).parent / "admin_token.json"))["user_id"]

def call(path, token):
    req = urllib.request.Request("http://localhost:8000" + path,
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def as_role(role, department=None):
    svc.table("profiles").update({"role": role, "department": department}).eq("id", UID).execute()
    return anon.auth.sign_in_with_password({"email": EMAIL, "password": PW}).session.access_token

checks = []
tok = as_role("guest")
s, _ = call("/api/reports", tok); checks.append(("guest GET /api/reports -> 403", s, s == 403))
s, _ = call("/api/agent/stats", tok); checks.append(("guest GET /api/agent/stats (admin-only) -> 403", s, s == 403))

tok = as_role("staff", "CSKH")
s, body = call("/api/reports?team=V%E1%BA%ADn%20h%C3%A0nh", tok)
ok = s in (200, 403)
if s == 200:
    data = json.loads(body) if body else {}
    # staff must be scoped to own dept: foreign-team query must not return foreign reports
    items = data.get("data", data if isinstance(data, list) else [])
    ok = all((r.get("team") == "CSKH") for r in items) if items else True
checks.append(("staff(CSKH) asks Vận hành reports -> scoped/denied", s, ok))
s, _ = call("/api/agent/stats", tok); checks.append(("staff GET admin-only stats -> 403", s, s == 403))

tok = as_role("manager", "CSKH")
s, _ = call("/api/reports", tok); checks.append(("manager GET /api/reports -> 200", s, s == 200))

tok = as_role("admin")
s, _ = call("/api/reports", tok); checks.append(("admin GET /api/reports -> 200", s, s == 200))

for name, status, ok in checks:
    print(("PASS" if ok else "FAIL"), f"[{status}]", name)
print("ALL PASS" if all(c[2] for c in checks) else "HAS FAILURES")
