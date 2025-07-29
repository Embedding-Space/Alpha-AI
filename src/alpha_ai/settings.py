"""Configuration settings for Alpha AI."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
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
    
    class Config:
        env_prefix = "ALPHA_AI_"
        

settings = Settings()