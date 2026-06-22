"""Quick smoke-test for the new hybrid RAG engine."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8 output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from agent.rag_engine import _vector_search, _keyword_search, _hybrid_merge
from services.embedding_service import CohereEmbeddingService

embedder = CohereEmbeddingService()

QUERIES = [
    "khách hàng phàn nàn tài xế chạy ẩu, vậy chính sách của công ty để xử lý việc này là như thế nào",
    "tài xế có thái độ xấu với khách, quy trình xử lý",
    "hoàn tiền khi bị trừ sai",
    "sla p5 là bao lâu",
]

for q in QUERIES:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    emb = embedder.embed_query(q)
    vr = _vector_search(emb, scope_team=None, top_k=6)
    kr = _keyword_search(q, scope_team=None, top_k=6)
    merged = _hybrid_merge(vr, kr, top_k=3)

    print(f"  Vector hits: {len(vr)}, Keyword hits: {len(kr)}")
    print("  Top merged results:")
    for i, r in enumerate(merged, 1):
        sim = r.get('similarity')
        sim_str = f"sim={sim:.3f}" if sim is not None else "sim=N/A (keyword only)"
        print(f"  [{i}] rrf={r['rrf_score']:.5f} | {sim_str}")
        print(f"       {r['document_title']} > {r['heading']}")
