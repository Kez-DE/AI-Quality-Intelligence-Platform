import os
import sys

# Ensure pipeline dir is in sys.path
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
if PIPELINE_DIR not in sys.path:
    sys.path.append(PIPELINE_DIR)

from ingest import get_supabase
from services.embedding_service import CohereEmbeddingService

embedder = CohereEmbeddingService()

query = "khách hàng phàn nàn tài xế chạy ẩu, vậy chính sách của công ty để xử lý việc này là như thế nào"
print(f"Embedding query: {query}")
emb = embedder.embed_query(query)
print(f"Embedding size: {len(emb)}")

db = get_supabase()
response = db.rpc("match_graph_nodes", {
    "query_embedding": emb,
    "match_count": 5,
    "department_filter": None
}).execute()

chunks = response.data or []
print(f"Found {len(chunks)} chunks.")
for c in chunks:
    try:
        print(f"ID: {c.get('id')}, Sim: {c.get('similarity')}")
        print(f"Title: {c.get('document_title')}")
        print(f"Content: {c.get('content')[:100]}")
        print("---")
    except Exception as e:
        print(f"Error printing chunk: {e}")
