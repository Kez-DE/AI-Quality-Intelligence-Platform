import os
from ingest import get_supabase

def check():
    try:
        db = get_supabase()
        nodes = db.table("graph_nodes").select("*", count="exact").limit(5).execute()
        edges = db.table("graph_edges").select("source_id", count="exact").limit(1).execute()
        
        node_count = nodes.count if nodes.count is not None else 0
        edge_count = edges.count if edges.count is not None else 0
        
        print(f"Nodes in Supabase: {node_count}")
        print(f"Edges in Supabase: {edge_count}")
        
        if node_count > 0:
            print("\nSample node 1:")
            first = nodes.data[0]
            print(f"- Type: {first.get('node_type')}")
            print(f"- Canonical Key: {first.get('canonical_key')}")
            print(f"- Name: {first.get('name')}")
            print(f"- Has Embedding: {'embedding' in first and first['embedding'] is not None}")
    except Exception as e:
        print(f"Error querying Supabase: {e}")

if __name__ == "__main__":
    check()
