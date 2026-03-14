"""
Centralized configuration management for the Finance Chatbot.
Uses Pydantic Settings for environment variable support.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    news_api_key: Optional[str] = Field(None, env="NEWS_API_KEY")
    alpha_vantage_key: Optional[str] = Field(None, env="ALPHA_VANTAGE_KEY")
    
    # LLM Configuration
    llm_model: str = Field("llama-3.1-8b-instant", env="LLM_MODEL")
    llm_temperature: float = Field(0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(1024, env="LLM_MAX_TOKENS")
    
    # Embedding Configuration
    embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2", 
        env="EMBEDDING_MODEL"
    )
    
    # Cache Configuration
    cache_ttl_market_data: int = Field(30, env="CACHE_TTL_MARKET")  # seconds
    cache_ttl_news: int = Field(300, env="CACHE_TTL_NEWS")  # 5 minutes
    cache_ttl_session: int = Field(3600, env="CACHE_TTL_SESSION")  # 1 hour
    
    # Server Configuration
    server_host: str = Field("0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(8000, env="SERVER_PORT")
    cors_origins: list[str] = Field(
        ["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    
    # Feature Flags
    enable_streaming: bool = Field(True, env="ENABLE_STREAMING")
    enable_websocket: bool = Field(True, env="ENABLE_WEBSOCKET")
    enable_news: bool = Field(True, env="ENABLE_NEWS")
    enable_portfolio: bool = Field(True, env="ENABLE_PORTFOLIO")
    
    # Market Configuration
    default_market: str = Field("NSE", env="DEFAULT_MARKET")  # NSE, BSE, US
    
    # RAG Configuration
    rag_chunk_size: int = Field(500, env="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(50, env="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(3, env="RAG_TOP_K")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
