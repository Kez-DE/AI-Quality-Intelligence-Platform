# 6 Departments Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the platform from 4 departments (IT, CSKH, Vận hành, Marketing) to 6 (IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận), re-routing tickets correctly and reassigning Marketing data to Sản phẩm — without regressing main's verified AI-report revamp.

**Architecture:** Extract only the 4→6 delta from branch `docs` and apply on `main` (no full merge). `DEPARTMENTS` in `pipeline/departments.py` is the single source of truth; `orchestrator.py` and `users_admin.py` already read it dynamically, so they need no change. Ticket routing lives in `data/taxonomy/routing_table.json` (config-driven). A data migration reassigns existing `Marketing` rows to `Sản phẩm`. `department` columns are plain TEXT with no CHECK constraint, so no schema change is required.

**Tech Stack:** Python (FastAPI, pytest) for `pipeline/`; React 19 + TanStack Start + Vitest for `app/`; Supabase Postgres migrations (SQL).

**Spec:** `docs/superpowers/specs/2026-06-27-six-departments-design.md`

**Branch:** `feat/six-departments` (already created off `main`).

**Test commands:**
- Pipeline: `cd pipeline && python -m pytest tests/<file> -v`
- Frontend: `cd app && npx vitest run` and `cd app && npx tsc --noEmit`

**Canonical 6 department strings (copy exactly, including diacritics):**
`IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận`

---

### Task 1: Department definition (`departments.py`)

**Files:**
- Modify: `pipeline/departments.py`
- Test: `pipeline/tests/test_departments.py`

**Step 1: Update the failing test**

Replace the body of `pipeline/tests/test_departments.py` with:

```python
from departments import DEPARTMENTS, alert_department, normalize_department


def test_departments_are_distinct_and_canonical():
    assert DEPARTMENTS == (
        "IT",
        "CSKH",
        "Vận hành",
        "Tài chính & Thanh toán",
        "Sản phẩm",
        "Quản lý Rủi ro & Gian lận",
    )
    assert len(set(DEPARTMENTS)) == 6


def test_normalize_legacy_department_aliases():
    assert normalize_department("Vận Hành") == "Vận hành"
    assert normalize_department("Vận hành & Đào tạo") == "Vận hành"
    assert normalize_department("Driver Mgmt") == "Vận hành"


def test_normalize_new_department_aliases():
    assert normalize_department("finance") == "Tài chính & Thanh toán"
    assert normalize_department("Thanh toán") == "Tài chính & Thanh toán"
    assert normalize_department("product") == "Sản phẩm"
    assert normalize_department("fraud") == "Quản lý Rủi ro & Gian lận"
    assert normalize_department("Rủi ro") == "Quản lý Rủi ro & Gian lận"


def test_marketing_no_longer_resolves():
    assert normalize_department("Marketing") is None


def test_alert_department_prefers_structured_field_and_supports_legacy():
    assert alert_department({
        "assigned_team": "Sản phẩm",
        "description": "**Assigned Team:** CSKH",
    }) == "Sản phẩm"
    assert alert_department({"description": "x\n**Assigned Team:** CSKH\n"}) == "CSKH"
```

**Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_departments.py -v`
Expected: FAIL (DEPARTMENTS still 4-tuple; new alias tests fail).

**Step 3: Implement**

In `pipeline/departments.py` replace the `DEPARTMENTS` tuple and `_DEPARTMENT_ALIASES` dict:

```python
DEPARTMENTS = (
    "IT",
    "CSKH",
    "Vận hành",
    "Tài chính & Thanh toán",
    "Sản phẩm",
    "Quản lý Rủi ro & Gian lận",
)

_DEPARTMENT_ALIASES = {
    "it": "IT",
    "cskh": "CSKH",
    "vận hành": "Vận hành",
    "vận hành & đào tạo": "Vận hành",
    "van hanh": "Vận hành",
    "driver mgmt": "Vận hành",
    "tài chính": "Tài chính & Thanh toán",
    "thanh toán": "Tài chính & Thanh toán",
    "finance": "Tài chính & Thanh toán",
    "sản phẩm": "Sản phẩm",
    "product": "Sản phẩm",
    "rủi ro": "Quản lý Rủi ro & Gian lận",
    "gian lận": "Quản lý Rủi ro & Gian lận",
    "risk": "Quản lý Rủi ro & Gian lận",
    "fraud": "Quản lý Rủi ro & Gian lận",
}
```

Also change the docstring of `normalize_department` from `"...one of the four RBAC departments."` to `"...one of the six RBAC departments."`.

**Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_departments.py -v`
Expected: PASS (all 5 tests).

**Step 5: Commit**

```bash
git add pipeline/departments.py pipeline/tests/test_departments.py
git commit -m "feat(departments): 6 phòng ban + alias finance/product/risk, bỏ Marketing"
```

---

### Task 2: Analyst personas (`analyst_agent.py`)

**Files:**
- Modify: `pipeline/agents/analyst_agent.py` (the `DEPARTMENT_PERSONAS` dict)

**Step 1: Implement** — In `DEPARTMENT_PERSONAS`, delete the entire `"Marketing": { ... }` entry and append these three (keep IT/CSKH/Vận hành unchanged):

```python
    "Tài chính & Thanh toán": {
        "persona": "Bạn là chuyên gia tài chính và đối soát thanh toán.",
        "priorities": "Tập trung giải quyết các khiếu nại về trừ tiền sai, lỗi đối soát, và yêu cầu hoàn tiền. Đảm bảo luồng tiền minh bạch.",
        "fallback_actions": [
            ("Rà soát các giao dịch thanh toán lỗi trong ngày", "24h"),
            ("Thực hiện hoàn tiền cho các khách hàng bị trừ lặp", "48h"),
            ("Kiểm tra và làm việc với đối tác cổng thanh toán", "1w"),
        ],
    },
    "Sản phẩm": {
        "persona": "Bạn là chuyên gia Quản lý Sản phẩm (Product Manager).",
        "priorities": "Tập trung vào trải nghiệm người dùng (UX/UI), tính năng bị lỗi hoặc gây bối rối, và đề xuất cải tiến sản phẩm.",
        "fallback_actions": [
            ("Thiết kế lại luồng UX/UI dựa trên phản hồi khách hàng", "1w"),
            ("Phối hợp với IT để sửa lỗi tính năng (bugs) khẩn cấp", "48h"),
            ("Khảo sát sâu người dùng về tính năng gây bối rối", "1w"),
        ],
    },
    "Quản lý Rủi ro & Gian lận": {
        "persona": "Bạn là chuyên gia phân tích dữ liệu rủi ro và gian lận.",
        "priorities": "Phát hiện lạm dụng khuyến mãi, cuốc xe ảo, và các tài khoản có hành vi bất thường. Đảm bảo an toàn hệ thống và giảm thất thoát.",
        "fallback_actions": [
            ("Rà soát và tạm khóa hàng loạt tài khoản lạm dụng khuyến mãi", "24h"),
            ("Tạo tập luật mới để phát hiện cuốc xe ảo tự động", "1w"),
            ("Điều tra sâu các cụm tài khoản có dấu hiệu thông đồng", "48h"),
        ],
    },
```

**Step 2: Verify it imports and runs**

Run: `cd pipeline && python -c "from agents.analyst_agent import DEPARTMENT_PERSONAS; assert set(DEPARTMENT_PERSONAS) == {'IT','CSKH','Vận hành','Tài chính & Thanh toán','Sản phẩm','Quản lý Rủi ro & Gian lận'}; print('ok')"`
Expected: `ok`

**Step 3: Commit**

```bash
git add pipeline/agents/analyst_agent.py
git commit -m "feat(analyst): persona cho Tài chính, Sản phẩm, Rủi ro & Gian lận; bỏ Marketing"
```

---

### Task 3: Ticket routing table (`routing_table.json`)

**Files:**
- Modify: `data/taxonomy/routing_table.json`
- Test: `pipeline/tests/test_router_agent.py`

**Step 1: Update the failing test** — In `pipeline/tests/test_router_agent.py`:

Change line 17 to `assert _team("Payment", "P3") == "Tài chính & Thanh toán"`.
Change the Pricing comment + line 20 to:
```python
    # Pricing giờ về Quản lý Rủi ro & Gian lận (lạm dụng KM, giá bất thường).
    assert _team("Pricing", "P3") == "Quản lý Rủi ro & Gian lận"
```
Change line 21 to `assert _team("Other", "P1", "positive") == "Sản phẩm"`.
Replace the `test_positive_sentiment_only_routes_marketing_for_other_topic` function with:
```python
def test_positive_sentiment_routes_san_pham_for_other_and_app_issue():
    # Positive CHUNG (Other) hoặc góp ý app (App Issue) -> Sản phẩm để nâng cấp UX.
    assert _team("Other", "P3", "positive") == "Sản phẩm"
    assert _team("App Issue", "P3", "positive") == "Sản phẩm"
    # Positive gắn chủ đề chuyên môn khác KHÔNG bị ép về Sản phẩm — route theo topic.
    assert _team("Payment", "P3", "positive") == "Tài chính & Thanh toán"
    assert _team("Driver Behavior", "P3", "positive") == "Vận hành"
    assert _team("Pricing", "P3", "positive") == "Quản lý Rủi ro & Gian lận"
```
In the override-missing-topics test, change the inline config's sentiment override team from `"Marketing"` to `"Sản phẩm"` (line ~41); the assertion that it is ignored stays.

**Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_router_agent.py -v`
Expected: FAIL (routing_table still routes Payment/Pricing→CSKH, positive→Marketing).

**Step 3: Implement** — In `data/taxonomy/routing_table.json` replace the Payment and Pricing routes and the sentiment override:

```json
    { "topic": "Payment",         "team": "Tài chính & Thanh toán", "sla_hours": 12, "priority_default": "P3", "description": "Vấn đề thanh toán, hoàn tiền, đối soát giao dịch." },
    { "topic": "Pricing",         "team": "Quản lý Rủi ro & Gian lận", "sla_hours": 12, "priority_default": "P3", "description": "Lạm dụng khuyến mãi, gian lận, giá cước bất thường." },
```

```json
  "sentiment_overrides": [
    { "sentiment": "positive", "topics": ["Other", "App Issue"], "team": "Sản phẩm", "sla_hours": 48, "priority_default": "P4", "description": "Phản hồi tích cực hoặc góp ý tính năng chuyển về Sản phẩm để nâng cấp UX/UI." }
  ]
```

**Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_router_agent.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add data/taxonomy/routing_table.json pipeline/tests/test_router_agent.py
git commit -m "feat(routing): Payment→Tài chính, Pricing→Rủi ro&Gian lận, positive→Sản phẩm"
```

---

### Task 4: Opportunity-ticket fix (`spike_detector.py`)

**Files:**
- Modify: `pipeline/spike_detector.py:146`
- Test: `pipeline/tests/test_spike_detector.py`

**Step 1: Update the failing test** — In `pipeline/tests/test_spike_detector.py`:

- Line ~38: change `{"area": "D", "topic": "Other", "team": "Marketing"}` → `{"area": "D", "topic": "Other", "team": "Sản phẩm"}`.
- Line ~43: change the expected list `["Vận hành", "IT", "Marketing"]` → `["Vận hành", "IT", "Sản phẩm"]`.
- Rename `test_positive_cluster_creates_marketing_opportunity` → `test_positive_cluster_creates_san_pham_opportunity`.
- Line ~173: change `self.assertEqual(kwargs["team"], "Marketing")` → `self.assertEqual(kwargs["team"], "Sản phẩm")`. Also assert ticket_type: add `self.assertEqual(kwargs["ticket_type"], "opportunity")` if not already present.

**Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_spike_detector.py -v`
Expected: FAIL (opportunity still keyed off "Marketing").

**Step 3: Implement** — In `pipeline/spike_detector.py` line 146, change:

```python
        ticket_type = "opportunity" if team == "Sản phẩm" and sentiment == "positive" else "incident"
```

**Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_spike_detector.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add pipeline/spike_detector.py pipeline/tests/test_spike_detector.py
git commit -m "fix(spike): ticket opportunity bám Sản phẩm thay vì Marketing đã bỏ"
```

---

### Task 5: Router fallback + comments (`router_agent.py`)

**Files:**
- Modify: `pipeline/agents/router_agent.py`

**Step 1: Implement** — Three edits (no behavior change since routing_table now supplies the team; this removes the dead "Marketing" default and stale prose):

- Line ~91: `team=normalize_department(override.get("team"), "Marketing"),` → `team=normalize_department(override.get("team"), "Sản phẩm"),`
- Docstring lines ~41 and inline comment ~79-81: replace "Marketing" with "Sản phẩm" and update wording (positive về Sản phẩm để nâng cấp UX).
- `__main__` example line ~154: `print(route_ticket("Other", 2, sentiment="positive"))  # -> Marketing` → `# -> Sản phẩm`.

**Step 2: Verify**

Run: `cd pipeline && python -m pytest tests/test_router_agent.py -v`
Expected: PASS (still green from Task 3).

Run: `git grep -n "Marketing" pipeline/agents/router_agent.py`
Expected: no output.

**Step 3: Commit**

```bash
git add pipeline/agents/router_agent.py
git commit -m "refactor(router): bỏ fallback/comment Marketing, dùng Sản phẩm"
```

---

### Task 6: Public KB tag (`build_public_kb.py`)

**Files:**
- Modify: `pipeline/scripts/build_public_kb.py:18`

**Step 1: Implement** — Change the category-4 tuple's third element from `"Marketing"` to `"Sản phẩm"`:

```python
    "4": ("khuyen_mai_uu_dai", "Khuyến mãi & ưu đãi", "Sản phẩm"),
```

**Step 2: Verify**

Run: `git grep -n "Marketing" pipeline/scripts/build_public_kb.py`
Expected: no output.

**Step 3: Commit**

```bash
git add pipeline/scripts/build_public_kb.py
git commit -m "chore(kb): tag phòng Sản phẩm thay Marketing trong public KB"
```

---

### Task 7: Sweep remaining test fixtures referencing Marketing

**Files (replace stray `"Marketing"` used as a sample department with `"Sản phẩm"`):**
- `pipeline/tests/test_auth_guard_manager.py`
- `pipeline/tests/test_feedback.py`
- `pipeline/tests/test_feedback_scope.py`
- `pipeline/tests/test_report_approval.py`
- `pipeline/tests/test_report_endpoint.py`
- `pipeline/tests/test_scoring_agent.py`
- `pipeline/tests/test_support_resolve.py`
- `pipeline/tests/test_task_lifecycle.py`
- `pipeline/tests/test_task_transitions.py`

**Step 1: Find every remaining occurrence**

Run: `cd pipeline && git grep -n "Marketing" tests/`
Read each hit. For each, replace the `"Marketing"` department literal with `"Sản phẩm"` (these use it only as a generic valid department in fixtures/assertions). Do NOT touch comments that merely explain history.

**Step 2: Run the full pipeline suite**

Run: `cd pipeline && python -m pytest tests/ -v`
Expected: PASS (no failures, no remaining Marketing department literals in assertions).

**Step 3: Confirm clean**

Run: `cd pipeline && git grep -n "Marketing" -- . ':!tests' ':!*.md'`
Expected: no output (all non-doc, non-migration code is Marketing-free).

**Step 4: Commit**

```bash
git add pipeline/tests/
git commit -m "test: cập nhật fixtures phòng ban Marketing→Sản phẩm"
```

---

### Task 8: Frontend department list (`api.ts`)

**Files:**
- Modify: `app/src/lib/api.ts:12-15` and comment at line ~26

**Step 1: Implement**

```typescript
export type Department =
  | "IT"
  | "CSKH"
  | "Vận hành"
  | "Tài chính & Thanh toán"
  | "Sản phẩm"
  | "Quản lý Rủi ro & Gian lận"
  | null;

/** 6 phòng ban — khớp backend DEPARTMENTS / profiles.department. */
export const ALL_TEAMS = [
  "IT",
  "CSKH",
  "Vận hành",
  "Tài chính & Thanh toán",
  "Sản phẩm",
  "Quản lý Rủi ro & Gian lận",
] as const;
```

Also update the `visibleTeams` doc comment "admin: cả 4 phòng" → "admin: cả 6 phòng".

**Step 2: Typecheck**

Run: `cd app && npx tsc --noEmit`
Expected: no new errors.

**Step 3: Commit**

```bash
git add app/src/lib/api.ts
git commit -m "feat(ui): ALL_TEAMS 6 phòng ban, bỏ Marketing"
```

---

### Task 9: Alerts dept map + opportunity label (`alerts.tsx`)

**Files:**
- Modify: `app/src/routes/_authenticated/alerts.tsx` (TEAM_CONFIG ~70-90, opportunity label ~476)

**Step 1: Implement** — In `TEAM_CONFIG`, delete the `Marketing:` entry and add three entries (reuse imported lucide icons; if `Megaphone` becomes unused, remove its import; add icons as needed, e.g. `Wallet`, `Package`, `ShieldAlert` from `lucide-react`):

```tsx
  "Tài chính & Thanh toán": {
    label: "Tài chính & Thanh toán",
    icon: Wallet,
    color: "text-emerald-700",
    bg: "bg-emerald-50 border-emerald-200",
  },
  "Sản phẩm": {
    label: "Sản phẩm",
    icon: Package,
    color: "text-orange-700",
    bg: "bg-orange-50 border-orange-200",
  },
  "Quản lý Rủi ro & Gian lận": {
    label: "Rủi ro & Gian lận",
    icon: ShieldAlert,
    color: "text-red-700",
    bg: "bg-red-50 border-red-200",
  },
```

Update the lucide-react import line to add `Wallet, Package, ShieldAlert` and drop `Megaphone` if no longer used.
Line ~476: change `Cơ hội Marketing` → `Cơ hội Sản phẩm`.

**Step 2: Typecheck + lint**

Run: `cd app && npx tsc --noEmit && npx eslint src/routes/_authenticated/alerts.tsx`
Expected: no errors (no unused-import warnings).

**Step 3: Commit**

```bash
git add app/src/routes/_authenticated/alerts.tsx
git commit -m "feat(ui): alerts hiển thị 3 phòng mới, nhãn Cơ hội Sản phẩm"
```

---

### Task 10: Department badge colors (`DepartmentBadge.tsx`)

**Files:**
- Modify: `app/src/components/DepartmentBadge.tsx` (`DEPT_STYLE`)

**Step 1: Implement** — In `DEPT_STYLE`, delete `Marketing` and add three keys:

```tsx
  "Tài chính & Thanh toán":
    "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30",
  "Sản phẩm":
    "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-500/10 dark:text-orange-300 dark:border-orange-500/30",
  "Quản lý Rủi ro & Gian lận":
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-300 dark:border-red-500/30",
```

**Step 2: Typecheck**

Run: `cd app && npx tsc --noEmit`
Expected: no errors.

**Step 3: Commit**

```bash
git add app/src/components/DepartmentBadge.tsx
git commit -m "feat(ui): màu badge cho 3 phòng mới, bỏ Marketing"
```

---

### Task 11: Data migration — reassign Marketing → Sản phẩm

**Files:**
- Create: `supabase/migrations/20260630000000_six_departments.sql`

**Step 1: Implement** — create the file:

```sql
-- Chuyển từ 4 sang 6 phòng ban.
-- Phòng hợp lệ: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận.
-- Marketing bị bỏ; user và dữ liệu lịch sử reassign về 'Sản phẩm' (phản hồi tích cực/UX).
-- LƯU Ý: profiles.department và alerts.assigned_team là TEXT, KHÔNG có CHECK constraint,
--        nên không cần đổi schema. Migration này idempotent (chạy lại no-op).

UPDATE public.profiles SET department = 'Sản phẩm' WHERE department = 'Marketing';
UPDATE public.alerts   SET assigned_team = 'Sản phẩm' WHERE assigned_team = 'Marketing';
UPDATE public.tasks    SET assigned_team = 'Sản phẩm' WHERE assigned_team = 'Marketing';

COMMENT ON COLUMN public.profiles.department IS
  'Canonical RBAC department: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận';
COMMENT ON COLUMN public.alerts.assigned_team IS
  'Team assignment: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận';
```

> Before running, confirm the `tasks` table's team column name. If it differs (e.g. `team` instead of `assigned_team`), adjust the third UPDATE. Check with: `git grep -nE "assigned_team|\\bteam\\b" supabase/migrations/*task*`.

**Step 2: Apply locally / to Supabase**

Run the project's migration command (per `supabase/README`, e.g. `supabase db push` or the harness migration runner). Then verify:

```sql
SELECT DISTINCT department FROM profiles;        -- no 'Marketing'
SELECT DISTINCT assigned_team FROM alerts;        -- no 'Marketing'
```
Expected: no `Marketing` rows remain.

**Step 3: Commit**

```bash
git add supabase/migrations/20260630000000_six_departments.sql
git commit -m "feat(db): migration reassign Marketing→Sản phẩm, 6 phòng ban"
```

---

### Task 12: Sync prose docs to 6 departments

**Files:**
- Modify: `co_che.md`, `docs/project/rbac-departments.md`, `docs/project/roadmap.md`
- Sweep: `MASTER_BLUEPRINT.md`, `docs/project/architecture.md`, `docs/project/agents-guide.md`, `docs/project/giai_thich.md` (only if they exist and mention 4 depts/Marketing)

**Step 1: Find all stale mentions**

Run: `git grep -nE "4 phòng ban|bốn phòng ban|Marketing" -- '*.md' ':!docs/superpowers' ':!docs/plans'`
Read each hit.

**Step 2: Edit**

- `docs/project/rbac-departments.md`: "## 4 phòng ban" → "## 6 phòng ban"; list the 6; update `valid_departments = [null, IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận]`; update the role↔department references and any diagram nodes (Marketing → the 3 new).
- `co_che.md`: §4 routing table (Payment→Tài chính, Pricing→Rủi ro&Gian lận, positive→Sản phẩm); §6 "Phòng ban" (6 phòng, remove the "Marketing" framing, keep the note that Safety/Pricing are topics not departments); §7 RBAC mermaid (replace `MKT[Marketing]` with the 3 new nodes) and `valid_departments`; §10 orchestrator Step 6-7 loop description ("for team in DEPARTMENTS"). Update the sentiment-override description in §4 from Marketing to Sản phẩm.
- `docs/project/roadmap.md`: move "Mở rộng 4 lên 6" from future to done — replace the intro caveat ("Hệ thống hiện chạy 4 phòng ban...") with "Hệ thống hiện chạy **6 phòng ban**" and mark the 4→6 section as ✅ đã triển khai (2026-06-27). Keep Global Report and other items as future.
- Sweep the four optional files; fix any "4 phòng ban"/Marketing wording.

**Step 3: Verify no stale mentions remain**

Run: `git grep -nE "4 phòng ban|bốn phòng ban" -- '*.md' ':!docs/superpowers' ':!docs/plans'`
Expected: no output. (Remaining "Marketing" should appear only as historical/migration notes, intentionally.)

**Step 4: Commit**

```bash
git add co_che.md docs/project/
git commit -m "docs: đồng bộ tài liệu sang 6 phòng ban (Tài chính, Sản phẩm, Rủi ro & Gian lận)"
```

---

### Task 13: Full verification

**Step 1: Run the whole pipeline suite**

Run: `cd pipeline && python -m pytest tests/ -v`
Expected: all PASS (especially `test_departments`, `test_router_agent`, `test_spike_detector`, and the AI-report tests `test_report_approval`/`test_report_builder` — confirms no report regression).

**Step 2: Frontend typecheck + tests**

Run: `cd app && npx tsc --noEmit && npx vitest run`
Expected: no type errors; tests pass.

**Step 3: Final Marketing audit**

Run: `git grep -n "Marketing" -- ':!supabase/migrations' ':!*.md'`
Expected: no output (code is Marketing-free; only historical migrations + intentional doc notes keep the word).

**Step 4: Confirm 6 departments end-to-end**

Run: `cd pipeline && python -c "from departments import DEPARTMENTS; print(DEPARTMENTS); assert len(DEPARTMENTS)==6"`
Expected: the 6-tuple printed.

**Step 5: Push the branch (only when the user asks) and open a PR**

```bash
git push -u origin feat/six-departments
```
Then summarize the change for a PR per the repo's high-risk lane (link the spec + this plan; note the data migration and that main's report revamp is untouched).
