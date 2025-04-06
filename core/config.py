from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App Configuration
    APP_NAME: str = "SHL Assessment Recommendation Engine"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: Optional[str] = None
    
    # Google Gemini API Configuration
    GEMINI_API_KEY: str
    
    # Recommendation Engine Configuration
    DEFAULT_TOP_K: int = 10
    MIN_SIMILARITY_THRESHOLD: float = 0.7
    RETRIEVAL_MULTIPLIER: int = 2  # How many more items to retrieve than top_k for reranking
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Create a global settings instance
settings = get_settings() 