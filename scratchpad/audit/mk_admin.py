"""Create throwaway admin for audit E2E; prints JWT. Cleanup: rm_admin.py."""
import os, sys, json
from pathlib import Path

for line in Path(__file__).resolve().parents[2].joinpath(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client

url = os.environ["SUPABASE_URL"]
svc = create_client(url, os.environ["SUPABASE_SERVICE_ROLE_KEY"])
EMAIL, PW = "audit-e2e-20260711@example.com", "Audit-E2E-20260711!x"

existing = [u for u in svc.auth.admin.list_users() if u.email == EMAIL]
user = existing[0] if existing else svc.auth.admin.create_user(
    {"email": EMAIL, "password": PW, "email_confirm": True}
).user
svc.table("profiles").update({"role": "admin"}).eq("id", user.id).execute()

anon = create_client(url, os.environ["SUPABASE_PUBLISHABLE_KEY"])
sess = anon.auth.sign_in_with_password({"email": EMAIL, "password": PW}).session
prof = svc.table("profiles").select("*").eq("id", user.id).execute().data
print(json.dumps({"user_id": user.id, "role": prof[0].get("role") if prof else None,
                  "token": sess.access_token}))
