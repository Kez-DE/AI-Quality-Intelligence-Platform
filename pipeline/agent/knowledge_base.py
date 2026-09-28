"""Keyword-based RAG retriever cho Knowledge Base (SOP/SLA/Tech/Tickets).

Vì KB rất nhỏ (~9 file, ~43 chunk) và DeepSeek không có embedding API, ta dùng
keyword retrieval (BM25-lite) thay cho vector search:
  - Load mọi file .md trong data/knowledge_base/.
  - Parse YAML frontmatter (department, category, severity_scope, tags).
  - Chunk theo heading cấp 2 (`##`); mỗi section là một chunk độc lập.
  - Tìm chunk liên quan bằng điểm overlap từ khóa (chuẩn hóa bỏ dấu để match bền),
    cộng IDF nhẹ + boost khi khớp tiêu đề/heading/tags.

Hỗ trợ lọc theo `department` để khớp cơ chế RBAC: ops chỉ tra cứu tài liệu phòng mình.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional

# Định vị data/knowledge_base bền ở cả local lẫn Docker:
#  - Local: pipeline/agent/knowledge_base.py -> ../../data/knowledge_base (gốc repo).
#  - Docker backend: nội dung pipeline/ nằm ở /app, data ở /app/data -> /app/data/knowledge_base.
# Thử lần lượt các ứng viên, lấy thư mục đầu tiên tồn tại.
def _resolve_kb_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("KNOWLEDGE_BASE_DIR"),
        os.path.normpath(os.path.join(here, "..", "..", "data", "knowledge_base")),  # local repo
        os.path.normpath(os.path.join(here, "..", "data", "knowledge_base")),         # docker: /app/agent -> /app/data
        "/app/data/knowledge_base",                                                    # docker tuyệt đối
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    # Fallback: trả ứng viên local để thông báo lỗi rõ ràng nếu thiếu data.
    return candidates[1]


_KB_DIR = _resolve_kb_dir()

# Từ dừng tiếng Việt/Anh phổ biến — loại để điểm tập trung vào từ khóa nghiệp vụ.
_STOPWORDS = {
    "la", "va", "co", "cua", "cho", "khi", "the", "nao", "gi", "thi", "mot", "cac",
    "nhung", "duoc", "voi", "trong", "tai", "ve", "den", "tu", "hay", "lam", "bi",
    # No "do" or "an": accent-stripped they are đồ/đỏ and ăn/"an toàn".
    "se", "da", "dang", "nay", "ra", "len", "xuong", "phai", "can", "neu",
    "the", "a", "the", "to", "of", "in", "on", "for", "and", "or", "is", "how",
    "what", "khong", "co", "bao", "nhieu", "may",
}


def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt: 'thanh toán' -> 'thanh toan' (match bền với gõ thiếu dấu)."""
    nfkd = unicodedata.normalize("NFD", text)
    no_marks = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return no_marks.replace("đ", "d").replace("Đ", "D")


def _tokenize(text: str) -> List[str]:
    norm = _strip_accents(text.lower())
    tokens = re.findall(r"[a-z0-9]+", norm)
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


def _parse_frontmatter(raw: str) -> tuple[Dict[str, Any], str]:
    """Tách YAML frontmatter đơn giản (key: value, value có thể là [list]) khỏi body."""
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta: Dict[str, Any] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            meta[key] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
        else:
            meta[key] = val
    return meta, parts[2].strip()


def _chunk_by_heading(body: str) -> List[Dict[str, str]]:
    """Cắt body theo heading cấp 2 (`## `). Phần trước H2 đầu tiên gộp vào chunk 'intro'."""
    chunks: List[Dict[str, str]] = []
    current_heading = "Tổng quan"
    current_lines: List[str] = []

    def flush():
        text = "\n".join(current_lines).strip()
        if text:
            chunks.append({"heading": current_heading, "content": text})

    for line in body.splitlines():
        if line.startswith("## "):
            flush()
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return chunks


@lru_cache(maxsize=1)
def _load_chunks() -> List[Dict[str, Any]]:
    """Load + chunk toàn bộ KB một lần (cache). Mỗi chunk kèm metadata cấp tài liệu."""
    chunks: List[Dict[str, Any]] = []
    if not os.path.isdir(_KB_DIR):
        return chunks

    for root, _dirs, files in os.walk(_KB_DIR):
        for fname in files:
            if not fname.endswith(".md") or fname == "README.md":
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                continue
            meta, body = _parse_frontmatter(raw)
            for idx, c in enumerate(_chunk_by_heading(body)):
                searchable = f"{meta.get('document_title', '')} {c['heading']} {c['content']} {' '.join(meta.get('tags', []))}"
                chunks.append({
                    "doc_id": fname,
                    "document_title": meta.get("document_title", fname),
                    "department": meta.get("department"),
                    "category": meta.get("category"),
                    "tags": meta.get("tags", []),
                    "heading": c["heading"],
                    "content": c["content"],
                    "chunk_index": idx,
                    "tokens": _tokenize(searchable),
                    "title_tokens": set(_tokenize(f"{meta.get('document_title', '')} {c['heading']} {' '.join(meta.get('tags', []))}")),
                })
    return chunks


@lru_cache(maxsize=1)
def _idf() -> Dict[str, float]:
    """IDF nhẹ trên tập chunk để hạ trọng số từ phổ biến."""
    chunks = _load_chunks()
    n = len(chunks) or 1
    df: Dict[str, int] = {}
    for c in chunks:
        for tok in set(c["tokens"]):
            df[tok] = df.get(tok, 0) + 1
    return {tok: math.log(1 + n / (1 + cnt)) for tok, cnt in df.items()}


def search_knowledge(query: str, department: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
    """Trả về top_k chunk liên quan nhất tới query.

    department: nếu set, chỉ tìm trong tài liệu của phòng đó (khớp RBAC).
    """
    chunks = _load_chunks()
    if not chunks:
        return []
    if department:
        scoped = [c for c in chunks if c.get("department") == department]
        # Có tài liệu của phòng -> chỉ tra trong đó; không có -> để rỗng (không leak phòng khác).
        chunks = scoped

    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    idf = _idf()

    scored = []
    for c in chunks:
        tok_counts: Dict[str, int] = {}
        for t in c["tokens"]:
            tok_counts[t] = tok_counts.get(t, 0) + 1
        score = 0.0
        for qt in set(q_tokens):
            if qt in tok_counts:
                # TF (bão hòa nhẹ) * IDF, + boost nếu từ khóa nằm ở tiêu đề/heading/tags.
                tf = 1 + math.log(tok_counts[qt])
                score += tf * idf.get(qt, 1.0)
                if qt in c["title_tokens"]:
                    score += 2.0 * idf.get(qt, 1.0)
        if score > 0:
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, c in scored[:top_k]:
        results.append({
            "doc_id": c["doc_id"],
            "document_title": c["document_title"],
            "department": c["department"],
            "category": c["category"],
            "heading": c["heading"],
            "content": c["content"],
            "score": round(score, 2),
        })
    return results


def format_for_prompt(results: List[Dict[str, Any]]) -> str:
    """Định dạng kết quả thành block trích dẫn để nhồi vào prompt LLM."""
    if not results:
        return "Không tìm thấy tài liệu nội bộ nào liên quan đến câu hỏi này."
    blocks = ["Tài liệu nội bộ liên quan (trích dẫn nguồn khi trả lời):"]
    for i, r in enumerate(results, 1):
        blocks.append(
            f"\n[Nguồn {i}] {r['document_title']} › {r['heading']} "
            f"(file: {r['doc_id']}, phòng: {r['department'] or 'chung'})\n{r['content']}"
        )
    return "\n".join(blocks)


if __name__ == "__main__":
    for q in ["xử lý tai nạn giao thông", "bị trừ tiền 2 lần", "tài xế thái độ kém"]:
        print(f"\n=== Q: {q} ===")
        for r in search_knowledge(q, top_k=2):
            print(f"  [{r['score']}] {r['doc_id']} › {r['heading']} (phòng {r['department']})")
