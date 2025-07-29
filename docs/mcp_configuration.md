# MCP Server Configuration

Alpha AI supports multiple MCP (Model Context Protocol) servers, allowing you to extend the AI agent's capabilities with various tools and integrations.

## Configuration Methods

### 1. Legacy Alpha Brain URL

For backward compatibility, you can still use the `ALPHA_BRAIN_URL` environment variable:

```bash
ALPHA_BRAIN_URL=http://localhost:9102/mcp/
```

### 2. MCP Configuration File (Recommended)

Use a Claude Desktop-compatible JSON configuration file to define multiple MCP servers:

```bash
MCP_CONFIG_FILE=/path/to/mcp_config.json
```

Example configuration file:

```json
{
  "mcpServers": {
    "alpha-brain": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:9102/mcp/"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@fetchmcp/fetch-mcp"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@cloudflare/mcp-server-filesystem", "/allowed/path"]
    }
  }
}
```

### 3. Selective Server Loading

You can choose which servers to load from the config file:

```bash
MCP_CONFIG_FILE=/path/to/mcp_config.json
MCP_SERVERS=alpha-brain,context7
```

## Supported MCP Server Types

### HTTP Remote Servers
Servers accessed via HTTP using `mcp-remote`:
- Alpha Brain
- Unirag
- Any HTTP-based MCP server

### Stdio Servers
Servers that communicate via standard input/output:
- Context7 (documentation lookup)
- Fetch (web content retrieval)
- Filesystem (local file access)
- Desktop Commander
- Todoish

## Docker Considerations

When running Alpha AI in Docker:
- Replace `localhost` with `host.docker.internal` for HTTP servers
- Stdio servers may require additional configuration for Docker compatibility

Example Docker-friendly configuration:

```json
{
  "mcpServers": {
    "alpha-brain": {
      "command": "npx",
      "args": ["mcp-remote", "http://host.docker.internal:9102/mcp/"]
    }
  }
}
```

## Checking Loaded Servers

The `/health` endpoint shows which MCP servers are loaded:

```bash
curl http://localhost:8100/health | jq
```

Response:
```json
{
  "status": "healthy",
  "model": "ollama:qwen2.5:14b",
  "alpha_brain_connected": false,
  "mcp_servers": ["context7", "fetch"]
}
```