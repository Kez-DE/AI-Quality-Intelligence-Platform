# 0013 Move persistence to a self-owned Supabase project

Date: 2026-08-26

## Status

Accepted

## Context

The platform stored all data in Supabase project `metadata_xanhsm`
(`fkopgtacyuejfzzfgtau`), which lived in a third-party organization we do not
own. As of 2026-08-26 that project no longer resolves in DNS
(`db.fkopgtacyuejfzzfgtau.supabase.co: no such host`) and reports `INACTIVE`,
so every local and Railway service that reads Supabase was already failing. We
could neither dump nor restore its data without dashboard access to an
organization we do not own.

## Decision

Provision a new Supabase project owned by the project's own organization and
repoint every consumer at it:

- Project `ai-quality-intelligence` (`gvtoqbowulwmpzfogjwp`), org
  `Kez-DE's Org` (`qbvfutsanngcohrzrdev`), region `ap-southeast-1`.
- Schema rebuilt from the 30 files in `supabase/migrations/` via
  `supabase db push --include-all`. No data migrated: the database starts
  empty by explicit choice, data is loaded later.
- `supabase/config.toml` `project_id` and the CLI link point at the new ref.
- New keys written to `.env` (publishable + legacy `service_role` JWT) and to
  all 7 Railway services in `friendly-encouragement`.
- `pipeline/mcp_http.py` hardcoded OAuth issuer fallback updated to the new
  project host.

## Alternatives Considered

1. Restore `metadata_xanhsm` from the Supabase dashboard and keep using it —
   rejected: the organization is not ours, so availability stays outside our
   control and the same outage can recur.
2. Create the new project inside the same third-party organization — rejected
   for the same ownership reason, plus its free-tier project slots are taken.

## Consequences

Positive:

- Data ownership now sits with the project owner; no dependency on a
  third-party organization for restore, key rotation, or billing.
- Schema is reproducible end-to-end from `supabase/migrations/`, proven by a
  clean push against an empty database.

Tradeoffs:

- All prior production data in `metadata_xanhsm` is not carried over and is
  effectively lost unless that project is restored later.
- Supabase Auth users are gone with it, so accounts must be recreated.

## Follow-Up

- Load data into the empty database (`data/demo/seed_demo_150.json` via
  `pipeline/ingest.py`, or real ingestion).
- Recreate the demo/admin accounts and RBAC rows in `profiles`.
- Historical references to `fkopgtacyuejfzzfgtau` in `docs/plans/` and
  `docs/superpowers/specs/` are left as-is: they record what was true then.
