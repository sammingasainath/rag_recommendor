from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from pathlib import Path


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SHL Assessment Recommendation API"
    APP_DESCRIPTION: str = "API for recommending SHL assessments based on job requirements"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]  # In production, set to specific origins

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"

    # Supabase settings
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")  # For privileged operations
    SUPABASE_ASSESSMENTS_TABLE: str = "assessments"
    SUPABASE_EMBEDDINGS_COLUMN: str = "embedding"

    # Gemini settings
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_EMBEDDING_MODEL: str = "models/embedding-001"
    GEMINI_TEXT_MODEL: str = "models/gemini-1.5-pro"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_TOP_P: float = 0.8
    GEMINI_TOP_K: int = 40
    GEMINI_MAX_TOKENS: int = 1024

    # RAG settings
    DEFAULT_TOP_K: int = 5
    MIN_SIMILARITY_THRESHOLD: float = 0.6
    RETRIEVAL_MULTIPLIER: int = 3
    ALWAYS_USE_LLM_RERANKING: bool = False
    
    # Testing and development settings
    USE_MOCK_DATA: bool = False  # Set to True to force use of mock data for testing

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = 'utf-8'
        extra = "ignore"  # Allow extra fields in the environment file


settings = Settings() 