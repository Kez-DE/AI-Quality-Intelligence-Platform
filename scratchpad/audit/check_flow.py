"""Stage-by-stage verification of the 30 ingested feedback rows."""
import os, re, json
from pathlib import Path

for line in Path(__file__).resolve().parents[2].joinpath(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
svc = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

rows = svc.table("feedback").select("*").order("created_at", desc=True).limit(30).execute().data
print(f"rows fetched: {len(rows)}")

PHONE = re.compile(r"(?<!\d)(0|\+84)\d{8,10}(?!\d)")
EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}")
PLATE = re.compile(r"\b\d{2}[A-Z]{1,2}[- ]?\d{3}\.?\d{2}\b")

problems = []
sev_dist, topic_dist, area_null = {}, {}, 0
for r in rows:
    text = (r.get("content") or r.get("text") or "")
    for name, rx in [("phone", PHONE), ("email", EMAIL), ("plate", PLATE)]:
        m = rx.search(text)
        if m:
            problems.append(f"PII {name} leaked in feedback {r.get('id')}: ...{text[max(0,m.start()-15):m.end()+10]}...")
    sev = r.get("severity"); sev_dist[sev] = sev_dist.get(sev, 0) + 1
    top = r.get("topic"); topic_dist[top] = topic_dist.get(top, 0) + 1
    if not r.get("area"): area_null += 1
    if sev is None: problems.append(f"feedback {r.get('id')}: severity NULL")
    if not top: problems.append(f"feedback {r.get('id')}: topic NULL")
    conf = r.get("confidence")
    if conf is not None and not (0 <= conf <= 1):
        problems.append(f"feedback {r.get('id')}: confidence out of range: {conf}")
    if r.get("severity") == "P5" and not r.get("needs_review"):
        problems.append(f"feedback {r.get('id')}: P5 but needs_review false")

print("severity dist:", json.dumps(sev_dist, ensure_ascii=False))
print("topic dist:", json.dumps(topic_dist, ensure_ascii=False))
print("area null count:", area_null)
sample = rows[0]
print("sample keys:", sorted(sample.keys()))
print("PROBLEMS:" if problems else "NO PROBLEMS")
for p in problems: print(" -", p)
