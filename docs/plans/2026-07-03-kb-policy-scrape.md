# Bổ sung KB từ chính sách thật — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Cào chính sách công khai xanhSM (greensm.com), làm mới public FAQ + soạn lại SOP nội bộ 6 phòng neo fact thật (tham khảo Be/Grab chỉ để mượn pattern, không vào repo), rồi re-index vector.

**Architecture:** Tái dùng nguyên `scrape_public_policy.py` (Firecrawl :3002, đã chạy) → `build_public_kb.py` → `seed_graph_kb.py`. Content Be/Grab chỉ nằm ở `/tmp` (không commit) làm tài liệu đọc. Guardrail: mọi FACT + liên hệ trong `data/` chỉ từ greensm.

**Tech Stack:** Firecrawl (docker :3002), Python 3.12, Supabase + Cohere (re-seed), pytest.

**Spec:** `docs/superpowers/specs/2026-07-03-kb-policy-scrape-design.md`
**Nhánh:** `feat/kb-policy-scrape` (trên nền `feat/mcp-server-and-improvements`).

Đã xác minh: Firecrawl `:3002` cào greensm OK (5865 ký tự); `test_kb_six_departments.py`, 3 SOP mới, và fix pytest crash đã có mặt trên nhánh nền.

---

## Task 1: Mở rộng nguồn cào greensm + chạy scrape

**Files:**
- Modify: `pipeline/scripts/scrape_public_policy.py`

**Step 1:** Mở rộng `SEED_URLS` — giữ 4 URL hiện có, thêm các trang chính sách nếu tồn tại (kiểm bằng cách để `discover_help_links` tự bắt; thêm thủ công những trang đã biết):
```python
SEED_URLS = [
    "https://www.greensm.com/vn-vi/helps",
    "https://www.greensm.com/vn-vi/terms-policies",
    "https://www.greensm.com/vn-vi/terms-policies/consumer-protection-policy",
    "https://www.greensm.com/vn-vi/terms-policies/privacy-notice",
    "https://www.greensm.com/vn-vi/terms-policies/operational-regulations",
    "https://www.greensm.com/vn-vi/terms-policies/terms-of-use",
]
```
Nới regex trong `discover_help_links` để bắt mọi path con `/terms-policies/*` và `/helps/*` (bỏ điều kiện hẹp nếu có).

**Step 2: Chạy scrape**
Run: `cd pipeline && .venv/bin/python scripts/scrape_public_policy.py`
Expected: in "XONG: N file vào /tmp/public_scrape"; `/tmp/public_scrape/_manifest.json` có ≥6 mục non-empty.

**Step 3: Verify**
Run: `ls /tmp/public_scrape/*.md | wc -l` và `cat /tmp/public_scrape/_manifest.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for x in d if x['chars']>100),'trang có nội dung')"`
Expected: ≥6 trang có nội dung.

**Step 4: Commit** (chỉ script; /tmp không commit)
```bash
git add pipeline/scripts/scrape_public_policy.py
git commit -m "feat(kb): mở rộng nguồn cào greensm (thêm trang terms-policies con)"
```

---

## Task 2: Cào Be/Grab tham khảo (KHÔNG commit content)

**Files:**
- Create: `pipeline/scripts/scrape_competitor_ref.py` (giống scrape nhưng output `/tmp/competitor_scrape/`, seed be.com.vn + grab.com/vn help/terms)

**Step 1:** Viết script phụ tái dùng hàm `scrape`/`_post` (import từ `scrape_public_policy`) với `OUT_DIR="/tmp/competitor_scrape"` và seed:
```python
SEED_URLS = [
    "https://www.be.com.vn/dieu-khoan",
    "https://www.be.com.vn/chinh-sach-bao-mat",
    "https://help.grab.com/passenger/vi-vn/",
]
```
(URL cụ thể chỉnh theo trang thật; nếu 404 → bỏ, ghi log.)

**Step 2: Chạy**
Run: `cd pipeline && .venv/bin/python scripts/scrape_competitor_ref.py`
Expected: file `.md` vào `/tmp/competitor_scrape/` (chỉ để đọc tham khảo).

**Step 3: Verify KHÔNG lẫn vào repo**
Run: `git status --short data/ | grep -i "be\|grab" || echo "sạch — không content competitor trong data/"`

**Step 4: Commit** (chỉ script, không content)
```bash
git add pipeline/scripts/scrape_competitor_ref.py
git commit -m "feat(kb): script cào Be/Grab tham khảo (output /tmp, không vào repo)"
```

---

## Task 3: Làm mới public KB (khách) từ greensm

**Files:**
- Modify (nếu parser lệch): `pipeline/scripts/build_public_kb.py`
- Regenerate: `data/public_kb/*.md`

**Step 1: Chạy build**
Run: `cd pipeline && .venv/bin/python scripts/build_public_kb.py`
Expected: ghi lại `data/public_kb/*.md`. Nếu lỗi parser (trang đổi cấu trúc) → chỉnh tối thiểu `parse_faqs`/`SECTIONS` cho khớp, chạy lại.

**Step 2: Verify nội dung thật + guardrail**
Run:
```bash
grep -rli "grab\|be\.com\.vn" data/public_kb/ && echo "LỖI: có competitor" || echo "sạch competitor"
grep -rc "audience: public" data/public_kb/*.md | head
```
Expected: sạch competitor; mỗi file có frontmatter.

**Step 3: Commit**
```bash
git add pipeline/scripts/build_public_kb.py data/public_kb/
git commit -m "feat(kb): làm mới public FAQ khách từ chính sách greensm thật"
```

---

## Task 4: Trích liên hệ xanhSM (nguồn duy nhất) + guardrail test

**Files:**
- Create: `pipeline/tests/test_kb_no_competitor.py`

**Step 1: Viết test guardrail (thất bại nếu có content competitor)**
```python
"""Guardrail: KB không được chứa liên hệ/tên miền của Be/Grab; chỉ greensm."""
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
KB_DIRS = [DATA / "knowledge_base", DATA / "public_kb"]
BANNED = re.compile(r"be\.com\.vn|grab\.com|help\.grab", re.I)


def _md_files():
    for d in KB_DIRS:
        yield from d.rglob("*.md")


def test_no_competitor_domain_in_kb():
    bad = [str(f) for f in _md_files() if BANNED.search(f.read_text(encoding="utf-8"))]
    assert not bad, f"KB chứa tên miền competitor: {bad}"


def test_kb_files_exist():
    assert any(_md_files()), "KB rỗng?"
```

**Step 2: Chạy**
Run: `cd pipeline && .venv/bin/python -m pytest tests/test_kb_no_competitor.py -q`
Expected: PASS (hiện chưa có competitor content).

**Step 3:** Xác định liên hệ xanhSM chuẩn từ `/tmp/public_scrape/` (hotline/email trên trang helps/contact greensm). Ghi lại giá trị để dùng thống nhất khi soạn SOP (Task 5-6). KHÔNG bịa — nếu trang không có số → để trống + ghi chú.

**Step 4: Commit**
```bash
git add pipeline/tests/test_kb_no_competitor.py
git commit -m "test(kb): guardrail chặn liên hệ/tên miền competitor trong KB"
```

---

## Task 5: Soạn/làm giàu SOP — nhóm khách hàng (CSKH, Tài chính & Thanh toán, Sản phẩm)

**Files:**
- Modify/Create: `data/knowledge_base/sop/*.md`, `data/knowledge_base/sla/*.md` cho 3 phòng

**Step 1:** Đọc `/tmp/public_scrape/` (consumer-protection, terms, payment) + `/tmp/competitor_scrape/` (pattern). Với mỗi phòng, cập nhật SOP:
- **CSKH:** quy trình khiếu nại, hoàn tiền, kênh hỗ trợ (liên hệ = greensm).
- **Tài chính & Thanh toán:** cước, thanh toán, hoàn tiền, đối soát — neo số/điều khoản thật từ greensm.
- **Sản phẩm:** khuyến mãi, điều kiện ưu đãi, tính năng app.
Mỗi file: frontmatter `department:` đúng tên chuẩn + `source: <URL greensm>` khi dùng fact thật. Pattern mượn ngành → ghi "tham khảo thông lệ ngành, không phải chính sách xanhSM chính thức". Liên hệ chỉ greensm.

**Step 2: Verify**
Run:
```bash
cd pipeline && .venv/bin/python -m pytest tests/test_kb_six_departments.py tests/test_kb_no_competitor.py -q
.venv/bin/python -c "
from agent.knowledge_base import search_knowledge
for d in ['CSKH','Tài chính & Thanh toán','Sản phẩm']:
    r = search_knowledge('quy trình hoàn tiền khiếu nại', department=d, top_k=2)
    print(d, '->', bool(r), any((x.get('department') or '')==d for x in r))
"
```
Expected: test pass; mỗi phòng trả doc đúng department.

**Step 3: Commit**
```bash
git add data/knowledge_base/
git commit -m "feat(kb): SOP CSKH/Tài chính/Sản phẩm neo chính sách greensm thật"
```

---

## Task 6: Soạn/làm giàu SOP — nhóm vận hành/rủi ro (Vận hành, Quản lý Rủi ro & Gian lận, IT)

**Files:**
- Modify/Create: `data/knowledge_base/sop/*.md`, `tech/*.md`

**Step 1:** Tương tự Task 5 cho:
- **Vận hành:** an toàn, xử lý sự cố/tai nạn tại hiện trường (neo chính sách an toàn greensm).
- **Quản lý Rủi ro & Gian lận:** gian lận cước, tài khoản giả, lạm dụng khuyến mãi.
- **IT:** lỗi kỹ thuật (thanh toán, không nhận cước) — phần này ít nguồn công khai → giữ nội bộ, ghi chú rõ.
Frontmatter + source như Task 5. Liên hệ chỉ greensm.

**Step 2: Verify**
```bash
cd pipeline && .venv/bin/python -m pytest tests/test_kb_six_departments.py tests/test_kb_no_competitor.py -q
.venv/bin/python -c "
from agent.knowledge_base import search_knowledge
for d in ['Vận hành','Quản lý Rủi ro & Gian lận','IT']:
    r = search_knowledge('xử lý sự cố an toàn gian lận', department=d, top_k=2)
    print(d, '->', bool(r))
"
```
Expected: pass; mỗi phòng ra doc.

**Step 3: Commit**
```bash
git add data/knowledge_base/
git commit -m "feat(kb): SOP Vận hành/Rủi ro&Gian lận/IT neo chính sách greensm thật"
```

---

## Task 7: Re-index vector (Supabase + Cohere)

> Mutation DB dùng chung (`seed_graph_kb.py` xóa+dựng lại `graph_nodes`). User đã đồng ý DB ops.

**Step 1: Chạy re-seed**
Run: `cd pipeline && .venv/bin/python seed_graph_kb.py`
Expected: "Seed Graph Database thành công"; node count tăng so với trước.

**Step 2: Verify hybrid search phủ nội dung mới**
```bash
cd pipeline && .venv/bin/python -c "
from agent.chat_tools import search_knowledge_base
for d in ['CSKH','Tài chính & Thanh toán','Sản phẩm','Vận hành','Quản lý Rủi ro & Gian lận']:
    out = search_knowledge_base('quy trình chính sách xử lý', scope_team=d)
    print(d, '->', '[Nguồn' in out)
"
```
Expected: mỗi phòng True.

**Không commit (mutation DB).**

---

## Task 8: Docs + guardrail cuối

**Files:**
- Modify: `docs/project/architecture.md` (mục `data/`: KB nội bộ giờ neo chính sách greensm thật, không còn thuần mock)
- Modify: `data/README.md` (provenance: nguồn greensm, ghi rõ Be/Grab chỉ tham khảo /tmp)
- Modify: `WORKLOG.md`

**Step 1:** Cập nhật 3 file trên.

**Step 2: Guardrail toàn cục cuối**
```bash
cd pipeline && .venv/bin/python -m pytest tests/ -q -k "kb or knowledge or rag or chat_tools"
grep -rEi "be\.com\.vn|grab\.com|help\.grab" ../data/ && echo "LỖI competitor" || echo "sạch"
grep -rE "0[0-9]{9,10}" ../data/knowledge_base/ | grep -viE "greensm|1900" | head   # rà số lạ (không phải hotline greensm)
```
Expected: test pass; sạch competitor.

**Step 3: Commit + push + PR**
```bash
git add docs data/README.md WORKLOG.md
git commit -m "docs(kb): provenance greensm + guardrail Be/Grab; cập nhật architecture/WORKLOG"
git push -u origin feat/kb-policy-scrape
gh pr create --title "feat(kb): bổ sung KB từ chính sách thật greensm (6 phòng)" --body "<tóm tắt + verify>"
```

## Thứ tự & phụ thuộc
1 → 2 (song song được với 3 sau khi 1 xong) → 3 → 4 → 5, 6 (cần /tmp scrape từ 1-2) → 7 → 8.

## Verify tổng
- `/tmp/public_scrape` ≥6 trang; public_kb làm mới; 6 phòng có SOP `department:`+`source:`.
- `test_kb_six_departments` + `test_kb_no_competitor` pass; grep sạch competitor + liên hệ chỉ greensm.
- Re-seed OK; hybrid search 6 phòng ra nội dung mới.
