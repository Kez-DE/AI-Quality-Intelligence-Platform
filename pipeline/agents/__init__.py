"""Multi-agent layer cho AI Quality Intelligence Platform.

Ported từ origin/main sang layout phẳng `pipeline/`:
- Import phẳng (agents.*, agent.model_router) thay cho `backend.pipeline.*`.
- LLM dùng OpenRouter qua agent.model_router (không phải Groq).
- Taxonomy đọc từ data/taxonomy/ ở repo root.
"""
