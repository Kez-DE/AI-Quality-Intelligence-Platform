import os
import sys
import json
import uuid
from pathlib import Path

# Thêm pipeline/ vào sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingest import get_supabase
from services.embedding_service import CohereEmbeddingService
from agent.knowledge_base import _load_chunks as load_internal_kb
from agent.public_kb import _load_public_chunks as load_public_kb
from core.paths import TAXONOMY_DIR

def main():
    print("Khởi tạo Supabase và Cohere...")
    db = get_supabase()
    embedder = CohereEmbeddingService()
    
    print("Xóa đồ thị cũ...")
    # Xóa tất cả nodes (edges tự động xóa do CASCADE)
    # Dùng cách an toàn để xóa toàn bộ
    db.table("graph_nodes").delete().neq("canonical_key", "dummy_never_match").execute()
    
    nodes_payload = []
    edges_payload = []
    node_map = {}
    
    def add_node(node_type, canonical_key, name, content, metadata=None):
        if canonical_key not in node_map:
            nid = str(uuid.uuid4())
            node_map[canonical_key] = nid
            nodes_payload.append({
                "id": nid,
                "node_type": node_type,
                "canonical_key": canonical_key,
                "name": name,
                "content": content,
                "metadata": metadata or {}
            })
        return node_map[canonical_key]
        
    def add_edge(source_key, target_key, rel_type):
        edges_payload.append({
            "source_id": node_map[source_key],
            "target_id": node_map[target_key],
            "relationship_type": rel_type
        })

    # 1. Parsing Routing Table
    routing_path = TAXONOMY_DIR / "routing_table.json"
    if routing_path.exists():
        with open(routing_path, "r", encoding="utf-8") as f:
            routing_data = json.load(f)
            
        for route in routing_data.get("routes", []):
            t_key = f"topic:{route['topic']}"
            d_key = f"dept:{route['team']}"
            add_node("Topic", t_key, f"Chủ đề: {route['topic']}", route.get("description", ""))
            add_node("Department", d_key, f"Phòng {route['team']}", f"Phòng ban xử lý mảng {route['team']}")
            add_edge(t_key, d_key, "ROUTES_TO")
            
    # 2. Load Internal KB
    internal_chunks = load_internal_kb()
    for idx, chunk in enumerate(internal_chunks):
        c_key = f"sop:internal:{chunk['doc_id']}:{chunk['chunk_index']}"
        dept = chunk.get("department")
        name = f"{chunk['document_title']} - {chunk['heading']}"
        content = f"{name}\n\n{chunk['content']}"
        add_node("SOPSection", c_key, name, content, {"source": "internal", "doc_id": chunk["doc_id"]})
        
        if dept:
            d_key = f"dept:{dept}"
            # Đảm bảo phòng ban tồn tại
            add_node("Department", d_key, f"Phòng {dept}", f"Phòng ban {dept}")
            add_edge(c_key, d_key, "BELONGS_TO")

    # 3. Load Public KB
    public_chunks = load_public_kb()
    for idx, chunk in enumerate(public_chunks):
        c_index = chunk.get('chunk_index', idx)
        c_key = f"sop:public:{chunk.get('doc_id', 'unknown')}:{c_index}"
        name = f"{chunk['document_title']} - {chunk['heading']}"
        content = f"{name}\n\n{chunk['content']}"
        add_node("SOPSection", c_key, name, content, {"source": "public", "doc_id": chunk["doc_id"]})
        
    print(f"Tổng số Node thu thập: {len(nodes_payload)}")
    print(f"Tổng số Edge thu thập: {len(edges_payload)}")
    
    # 4. Generate Embeddings
    print("Đang nhúng Vector bằng Cohere...")
    texts_to_embed = [n["content"] for n in nodes_payload]
    embeddings = []
    # Batch processing for cohere api
    for i in range(0, len(texts_to_embed), 50):
        batch = texts_to_embed[i:i+50]
        emb_batch = embedder.embed_texts(batch)
        embeddings.extend(emb_batch)
        
    for i, n in enumerate(nodes_payload):
        n["embedding"] = embeddings[i]
        
    # 5. Insert Database
    print("Lưu Nodes vào Database...")
    for i in range(0, len(nodes_payload), 50):
        db.table("graph_nodes").insert(nodes_payload[i:i+50]).execute()
        
    print("Lưu Edges vào Database...")
    for i in range(0, len(edges_payload), 50):
        db.table("graph_edges").insert(edges_payload[i:i+50]).execute()
        
    print("✅ Seed Graph Database thành công!")

if __name__ == "__main__":
    main()
