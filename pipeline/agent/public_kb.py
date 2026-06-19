"""Public KB retriever — RAG cho CHATBOT KHÁCH (guest).

TÁCH HOÀN TOÀN khỏi knowledge_base.py (KB nội bộ): đọc data/public_kb/ (chính sách,
FAQ công khai cào từ greensm.com). Khách KHÔNG bao giờ chạm tới SOP/SLA nội bộ.

Tái dùng các hàm parse/score thuần (không phụ thuộc thư mục) từ knowledge_base.py,
chỉ thay nguồn dữ liệu sang public_kb và bỏ filter department (khách không có phòng ban).
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from typing import Any, Dict, List

from .knowledge_base import _tokenize, _parse_frontmatter, _chunk_by_heading


def _resolve_public_kb_dir() -> str:
    """Định vị data/public_kb bền ở cả local lẫn Docker (giống knowledge_base)."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("PUBLIC_KB_DIR"),
        os.path.normpath(os.path.join(here, "..", "..", "data", "public_kb")),  # local repo
        os.path.normpath(os.path.join(here, "..", "data", "public_kb")),         # docker /app/agent
        "/app/data/public_kb",                                                    # docker tuyệt đối
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return candidates[1]


_PUBLIC_KB_DIR = _resolve_public_kb_dir()


@lru_cache(maxsize=1)
def _load_public_chunks() -> List[Dict[str, Any]]:
    """Load + chunk toàn bộ public KB một lần (cache)."""
    chunks: List[Dict[str, Any]] = []
    if not os.path.isdir(_PUBLIC_KB_DIR):
        return chunks
    for root, _dirs, files in os.walk(_PUBLIC_KB_DIR):
        for fname in files:
            if not fname.endswith(".md") or fname == "README.md":
                continue
            try:
                with open(os.path.join(root, fname), "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                continue
            meta, body = _parse_frontmatter(raw)
            # Chỉ nhận tài liệu công khai (chốt chặn an toàn: bỏ qua file thiếu audience: public)
            if str(meta.get("audience", "")).strip().lower() != "public":
                continue
            for idx, c in enumerate(_chunk_by_heading(body)):
                searchable = f"{meta.get('document_title', '')} {c['heading']} {c['content']}"
                chunks.append({
                    "doc_id": fname,
                    "document_title": meta.get("document_title", fname),
                    "category": meta.get("category"),
                    "source_url": meta.get("source_url", ""),
                    "heading": c["heading"],
                    "content": c["content"],
                    "tokens": _tokenize(searchable),
                    "title_tokens": set(_tokenize(f"{meta.get('document_title', '')} {c['heading']}")),
                })
    return chunks


@lru_cache(maxsize=1)
def _public_idf() -> Dict[str, float]:
    chunks = _load_public_chunks()
    n = len(chunks) or 1
    df: Dict[str, int] = {}
    for c in chunks:
        for tok in set(c["tokens"]):
            df[tok] = df.get(tok, 0) + 1
    return {tok: math.log(1 + n / (1 + cnt)) for tok, cnt in df.items()}


def search_public_knowledge(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Tìm top_k chunk công khai liên quan nhất tới câu hỏi của khách."""
    chunks = _load_public_chunks()
    if not chunks:
        return []
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    idf = _public_idf()

    scored = []
    for c in chunks:
        tok_counts: Dict[str, int] = {}
        for t in c["tokens"]:
            tok_counts[t] = tok_counts.get(t, 0) + 1
        score = 0.0
        for qt in set(q_tokens):
            if qt in tok_counts:
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
            "category": c["category"],
            "source_url": c["source_url"],
            "heading": c["heading"],
            "content": c["content"],
            "score": round(score, 2),
        })
    return results


def format_public_for_prompt(results: List[Dict[str, Any]]) -> str:
    """Định dạng kết quả thành block để nhồi vào prompt chatbot khách."""
    if not results:
        return ("Không tìm thấy thông tin chính sách phù hợp. Hãy hướng khách liên hệ "
                "Hotline 1555, email support.vn@greensm.com, hoặc mục Hỗ trợ trong ứng dụng.")
    blocks = ["Thông tin chính sách/hỗ trợ Green SM liên quan (dùng để trả lời khách, không bịa thêm):"]
    for i, r in enumerate(results, 1):
        blocks.append(f"\n[Mục {i}] {r['document_title']} › {r['heading']}\n{r['content']}")
    return "\n".join(blocks)


if __name__ == "__main__":
    print("Public KB dir:", _PUBLIC_KB_DIR)
    print("Chunks:", len(_load_public_chunks()))
    for q in ["làm sao gửi khiếu nại", "bị trừ tiền hai lần", "thêm phương thức thanh toán", "góp ý ứng dụng"]:
        print(f"\n=== Q: {q} ===")
        for r in search_public_knowledge(q, top_k=2):
            print(f"  [{r['score']}] {r['doc_id']} › {r['heading']}")
