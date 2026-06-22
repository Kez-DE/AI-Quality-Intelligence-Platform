-- Kích hoạt extension vector nếu chưa có
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Tạo bảng graph_nodes
CREATE TABLE IF NOT EXISTS public.graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type TEXT NOT NULL,         -- Ví dụ: 'Topic', 'Department', 'SOPSection', 'Severity'
    canonical_key TEXT NOT NULL,     -- Ví dụ: 'topic:refund', 'dept:Safety'
    name TEXT NOT NULL,              -- Tên hiển thị
    content TEXT,                    -- Chứa nội dung text (để nhúng vector và làm context)
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(1024),          -- Cohere embed-multilingual-v3.0 có 1024 chiều
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(node_type, canonical_key)
);

-- Tạo bảng graph_edges
CREATE TABLE IF NOT EXISTS public.graph_edges (
    source_id UUID REFERENCES public.graph_nodes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES public.graph_nodes(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL, -- Ví dụ: 'ROUTES_TO', 'HAS_SLA', 'REQUIRES_SOP'
    weight FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (source_id, target_id, relationship_type)
);

-- Tạo Index HNSW để tăng tốc độ tìm kiếm vector (Cosine Similarity)
CREATE INDEX IF NOT EXISTS graph_nodes_embedding_idx 
ON public.graph_nodes 
USING hnsw (embedding vector_cosine_ops);

-- Bật RLS và cấp quyền cho Authenticated/Service Role
ALTER TABLE public.graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.graph_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access for authenticated users on graph_nodes"
    ON public.graph_nodes FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow read access for authenticated users on graph_edges"
    ON public.graph_edges FOR SELECT
    TO authenticated
    USING (true);

-- Service Role (backend) có toàn quyền
CREATE POLICY "Service role full access graph_nodes"
    ON public.graph_nodes FOR ALL
    TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access graph_edges"
    ON public.graph_edges FOR ALL
    TO service_role
    USING (true) WITH CHECK (true);
