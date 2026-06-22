-- Hàm RPC tìm kiếm vector cho RAG
CREATE OR REPLACE FUNCTION match_graph_nodes (
  query_embedding vector(1024),
  match_count int DEFAULT 3,
  department_filter text DEFAULT NULL
) RETURNS TABLE (
  id uuid,
  document_title text,
  heading text,
  content text,
  department text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    gn.id,
    gn.name as document_title,
    gn.name as heading,
    gn.content,
    gn.metadata->>'department' as department,
    1 - (gn.embedding <=> query_embedding) as similarity
  FROM graph_nodes gn
  WHERE gn.node_type = 'SOPSection'
    AND (department_filter IS NULL OR (gn.metadata->>'department') = department_filter OR department_filter = 'admin')
  ORDER BY gn.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
