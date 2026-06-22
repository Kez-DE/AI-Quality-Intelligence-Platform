import os
import sys

# Ensure pipeline dir is in sys.path
PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PIPELINE_DIR not in sys.path:
    sys.path.append(PIPELINE_DIR)

from ingest import get_supabase
from services.embedding_service import CohereEmbeddingService
from agent.model_router import chat_completion, ChatMessage
from agent.knowledge_base import search_knowledge
from clean import mask_pii

embedder = CohereEmbeddingService()

RAG_SYSTEM_PROMPT = """Bạn là trợ lý AI nội bộ của XanhSM.
Bạn ĐƯỢC CUNG CẤP một danh sách các tài liệu hướng dẫn nghiệp vụ (SOP/SLA) liên quan trực tiếp đến câu hỏi của người dùng.
NHIỆM VỤ CỦA BẠN:
1. Trả lời câu hỏi DỰA HOÀN TOÀN vào tài liệu được cung cấp. Không được tự bịa thông tin.
2. Trích dẫn nguồn tài liệu bằng cách sử dụng cấu trúc [Nguồn X] (trong đó X là số thứ tự nguồn).
3. Nếu tài liệu được cung cấp không chứa thông tin để trả lời câu hỏi, hãy trả lời chính xác câu này: "Tôi không tìm thấy hướng dẫn nào trong sổ tay. Bạn có muốn tự tạo một Ticket chuyển lên cấp cao hơn không?"
"""

# Minimum content length to exclude short Topic/Department nodes
_MIN_CONTENT_LEN = 80

# RRF constant — controls how much lower ranks are penalised (standard = 60)
_RRF_K = 60


def _rrf_score(rank: int) -> float:
    """Reciprocal Rank Fusion score for a given 1-based rank."""
    return 1.0 / (_RRF_K + rank)


def _vector_search(query_emb: list, scope_team: str | None, top_k: int) -> list[dict]:
    """Vector similarity search via Supabase RPC.
    Filters out short stub nodes (Topic/Department) by content length.
    """
    db = get_supabase()
    try:
        response = db.rpc(
            "match_graph_nodes",
            {
                "query_embedding": query_emb,
                "match_count": top_k * 3,  # fetch extra to compensate for stub filtering
                "department_filter": scope_team if scope_team else None,
            },
        ).execute()
        raw = response.data or []
    except Exception as e:
        print(f"[rag_engine] Vector search error: {e}", flush=True)
        return []

    # Filter out stub nodes (Topics, Departments) which have very short content
    filtered = [c for c in raw if len(c.get("content", "")) >= _MIN_CONTENT_LEN]
    return filtered[:top_k]


def _keyword_search(query: str, scope_team: str | None, top_k: int) -> list[dict]:
    """BM25-lite keyword search from the local Markdown knowledge base."""
    try:
        results = search_knowledge(query, department=scope_team, top_k=top_k)
        return results
    except Exception as e:
        print(f"[rag_engine] Keyword search error: {e}", flush=True)
        return []


def _hybrid_merge(
    vector_results: list[dict],
    keyword_results: list[dict],
    top_k: int,
) -> list[dict]:
    """Merge vector and keyword results using Reciprocal Rank Fusion (RRF).

    Each candidate is identified by its (document_title, heading) pair so we
    can deduplicate across the two lists.

    Returns at most `top_k` results, sorted by combined RRF score (descending).
    The returned dicts include a `rrf_score` field for transparency.
    """
    # Build candidate pool indexed by (document_title, heading)
    pool: dict[tuple, dict] = {}

    def _key(item: dict) -> tuple:
        """Normalised dedup key.

        Vector chunks stored in Supabase have a `document_title` like
        "SOP-OPS-01 - Bước 1 — Tiếp nhận..." (title + heading concatenated).
        Keyword chunks have separate `document_title` and `heading` fields.
        We normalise by taking only the first 60 chars of each field lowercased
        so near-duplicates collapse into the same bucket.
        """
        dt = (item.get("document_title") or "").strip().lower()
        hd = (item.get("heading") or "").strip().lower()
        # If heading is contained inside document_title (vector chunk pattern), use only dt
        if hd and hd in dt:
            return (dt[:80],)
        return (dt[:60], hd[:60])


    # Add vector results
    for rank, item in enumerate(vector_results, start=1):
        k = _key(item)
        if k not in pool:
            pool[k] = {
                "document_title": item.get("document_title"),
                "heading": item.get("heading"),
                "department": item.get("department"),
                "content": item.get("content", ""),
                "similarity": item.get("similarity"),
                "rrf_vector": _rrf_score(rank),
                "rrf_keyword": 0.0,
            }
        else:
            pool[k]["rrf_vector"] = max(pool[k]["rrf_vector"], _rrf_score(rank))

    # Add keyword results
    for rank, item in enumerate(keyword_results, start=1):
        k = _key(item)
        if k not in pool:
            pool[k] = {
                "document_title": item.get("document_title"),
                "heading": item.get("heading"),
                "department": item.get("department"),
                "content": item.get("content", ""),
                "similarity": None,
                "rrf_vector": 0.0,
                "rrf_keyword": _rrf_score(rank),
            }
        else:
            pool[k]["rrf_keyword"] = max(pool[k]["rrf_keyword"], _rrf_score(rank))

    # Compute combined RRF score and sort
    scored = []
    for item in pool.values():
        combined = item["rrf_vector"] + item["rrf_keyword"]
        scored.append((combined, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, item in scored[:top_k]:
        item["rrf_score"] = round(score, 6)
        results.append(item)
    return results


def rag_chat(messages: list[ChatMessage], scope_team: str | None = None) -> dict:
    """Xử lý câu hỏi RAG với Hybrid Search: Vector + BM25 kết hợp bằng RRF."""

    # 1. Trích xuất câu hỏi cuối cùng của user
    last_user_q = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user" and m.get("content")),
        "",
    )
    if not last_user_q:
        return {"content": "Tôi không nhận được câu hỏi nào từ bạn.", "sources": []}

    safe_q = mask_pii(last_user_q)

    # 2. Song song: vector search + keyword search
    query_emb = embedder.embed_query(safe_q)
    vector_results = _vector_search(query_emb, scope_team, top_k=6)
    keyword_results = _keyword_search(safe_q, scope_team, top_k=6)

    print(
        f"[rag_engine] Vector: {len(vector_results)} hits, Keyword: {len(keyword_results)} hits",
        flush=True,
    )

    # 3. Hybrid merge
    merged = _hybrid_merge(vector_results, keyword_results, top_k=4)

    # 4. Chuẩn bị sources (Context Panel) và LLM Prompt
    sources = []
    context_blocks = []

    for idx, item in enumerate(merged, start=1):
        sources.append(
            {
                "document_title": item["document_title"],
                "heading": item["heading"],
                "department": item.get("department"),
                "similarity": item.get("similarity"),
                "rrf_score": item.get("rrf_score"),
                "content": item["content"],
            }
        )
        context_blocks.append(
            f"[Nguồn {idx}] {item['document_title']} - {item['heading']}\n{item['content']}"
        )

    context_str = "\n\n".join(context_blocks)
    if not context_str:
        context_str = "(Không tìm thấy tài liệu phù hợp trong cơ sở dữ liệu)"

    system_prompt = RAG_SYSTEM_PROMPT + f"\n\nTÀI LIỆU CUNG CẤP:\n{context_str}"

    # 5. Lọc PII từ tin nhắn cũ và gọi LLM
    current_messages = [{"role": "system", "content": system_prompt}]
    for m in messages:
        if m.get("role") == "system":
            continue
        m_copy = dict(m)
        if m_copy.get("content"):
            m_copy["content"] = mask_pii(m_copy["content"])
        current_messages.append(m_copy)

    try:
        result = chat_completion(current_messages, temperature=0.3)
    except Exception as e:
        raise e

    answer = mask_pii(result.get("content", ""))

    return {
        "content": answer,
        "sources": sources,
        "provider": result.get("provider", "unknown"),
        "model": result.get("model", "unknown"),
        "latency_ms": result.get("latency_ms", 0),
    }
