"""Configuration settings for Alpha AI."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Model configuration
    default_model: str = "ollama:qwen2.5:14b"
    
    # Context window settings
    conversation_window_size: int = 10
    
    # Database
    database_url: str = "sqlite:///./alpha_ai.db"
    
    # Alpha Brain connection
    alpha_brain_url: Optional[str] = None
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    
    # Provider configurations
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434/v1"
        

settings = Settings()