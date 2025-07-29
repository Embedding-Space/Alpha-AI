"""MCP server configuration and loading."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    
    def is_http_remote(self) -> bool:
        """Check if this is an HTTP remote server (using mcp-remote)."""
        return (
            self.command == "npx" and 
            len(self.args) >= 2 and 
            self.args[0] == "mcp-remote" and
            self.args[1].startswith("http")
        )
    
    def get_http_url(self) -> Optional[str]:
        """Extract HTTP URL from mcp-remote config."""
        if self.is_http_remote():
            return self.args[1]
        return None


class MCPConfig(BaseModel):
    """Full MCP configuration matching Claude Desktop format."""
    mcpServers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    globalShortcut: str = ""


def load_mcp_config(config_path: Path) -> MCPConfig:
    """Load MCP configuration from a JSON file."""
    with open(config_path, 'r') as f:
        data = json.load(f)
    return MCPConfig(**data)


def create_mcp_servers(config: MCPConfig, filter_servers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Create MCP server instances from configuration.
    
    Args:
        config: The MCP configuration
        filter_servers: Optional list of server names to include. If None, all servers are created.
        
    Returns:
        Dictionary mapping server name to MCP server instance
    """
    servers = {}
    
    for name, server_config in config.mcpServers.items():
        # Skip if we're filtering and this server isn't in the list
        if filter_servers and name not in filter_servers:
            continue
            
        try:
            if server_config.is_http_remote():
                # HTTP remote server
                url = server_config.get_http_url()
                if url:
                    servers[name] = MCPServerStreamableHTTP(
                        url,
                        tool_prefix=name  # Prefix tools with server name
                    )
                    print(f"Created HTTP MCP server '{name}' at {url} (tools prefixed with '{name}_')")
            else:
                # Stdio server with increased timeout for npm/npx downloads
                servers[name] = MCPServerStdio(
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env,
                    timeout=60.0,  # 60 second timeout for initialization
                    tool_prefix=name  # Prefix tools with server name
                )
                print(f"Created stdio MCP server '{name}' with command: {server_config.command} {' '.join(server_config.args)} (tools prefixed with '{name}_')")
        except Exception as e:
            print(f"Warning: Failed to create MCP server '{name}': {e}")
            
    return servers


def create_mcp_servers_from_file(
    config_path: Path | str, 
    filter_servers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to load config and create servers in one step.
    
    Args:
        config_path: Path to the MCP configuration JSON file
        filter_servers: Optional list of server names to include
        
    Returns:
        Dictionary mapping server name to MCP server instance
    """
    config_path = Path(config_path)
    config = load_mcp_config(config_path)
    return create_mcp_servers(config, filter_servers)