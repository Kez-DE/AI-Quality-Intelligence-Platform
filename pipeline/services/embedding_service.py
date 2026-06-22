import os
import cohere
from typing import List

class CohereEmbeddingService:
    def __init__(self):
        api_key = os.environ.get("COHERE_API_KEY")
        if not api_key:
            raise ValueError("COHERE_API_KEY is not set in the environment variables.")
        # Khởi tạo Cohere Client
        self.client = cohere.Client(api_key=api_key)
        self.model = "embed-multilingual-v3.0"
        
    def embed_texts(self, texts: List[str], input_type: str = "search_document") -> List[List[float]]:
        """
        Nhúng danh sách văn bản thành vector.
        input_type có thể là "search_document" (dùng khi lưu data vào DB) 
        hoặc "search_query" (dùng khi user đặt câu hỏi).
        """
        if not texts:
            return []
            
        # Gọi API Cohere
        response = self.client.embed(
            texts=texts,
            model=self.model,
            input_type=input_type
        )
        return response.embeddings
        
    def embed_query(self, query: str) -> List[float]:
        """Tiện ích nhúng 1 câu hỏi (dùng trong agent)"""
        return self.embed_texts([query], input_type="search_query")[0]
