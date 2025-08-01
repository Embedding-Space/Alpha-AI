"""Configuration settings for Alpha AI."""

from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    
    # Context window settings
    conversation_window_size: int = 10
    
    # Database
    database_url: str = "sqlite:///./data/alpha_ai.db"
    
    # UI feature flags
    streaming: bool = True  # Show streaming toggle in UI
    
    # MCP servers configuration file (Claude Desktop format)
    mcp_config_file: Optional[str] = None
    
    # List of MCP servers to enable (if None, all servers in config are enabled)
    mcp_servers: Optional[List[str]] = None
    
    def model_post_init(self, __context):
        """Post-initialization to handle comma-separated MCP_SERVERS."""
        # Handle comma-separated MCP_SERVERS environment variable
        import os
        mcp_servers_env = os.environ.get('MCP_SERVERS')
        if mcp_servers_env and not self.mcp_servers:
            self.mcp_servers = [s.strip() for s in mcp_servers_env.split(',') if s.strip()]
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    
    # Provider configurations
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434/v1"
        

settings = Settings()