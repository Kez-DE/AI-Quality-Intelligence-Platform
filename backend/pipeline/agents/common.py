import os
import json
from groq import Groq
from supabase import create_client, Client
from backend.pipeline.env_config import get_supabase_config

# Initialize Supabase client
def get_db() -> Client:
    url, key = get_supabase_config()
    if not url or not key:
        raise ValueError("Supabase URL or Key is missing from environment variables.")
    return create_client(url, key)

# Initialize Groq client
def get_llm_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    return Groq(api_key=api_key)

def call_llm(system_prompt: str, user_message: str, model: str = "llama-3.3-70b-versatile", response_format: str = "text") -> str:
    """
    Calls the Groq LLM API.
    Used by agents for analysis tasks. Ensures context isolation.
    """
    client = get_llm_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # Configure json mode if requested
    params = {
        "messages": messages,
        "model": model,
        "temperature": 0.1,
    }
    
    if response_format == "json_object":
         params["response_format"] = {"type": "json_object"}
         
    try:
        completion = client.chat.completions.create(**params)
        return completion.choices[0].message.content or ""
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return ""
