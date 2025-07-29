# Alpha-AI

Provider-agnostic AI agent server with REST API, MCP bridge, and web UI.

## Overview

Alpha-AI creates Alpha-architecture AI instances across different models and frontends. It combines system prompt + Alpha Brain tools + model into a cohesive Agent, exposing this via REST API.

## Components

- **alpha-ai**: Core REST API server with web UI (runs in Docker)
- **alpha-ai-mcp**: stdio MCP bridge for Claude Code/Desktop integration

## Quick Start

```bash
# Start the stack
docker compose up -d

# Open web UI at http://localhost:8100

# Or use with Claude Code/Desktop via MCP
uv run alpha-mcp
```

### Using MCP Servers

1. Copy the example MCP config:
```bash
cp mcp_config.example.json mcp_config.json
```

2. Edit `mcp_config.json` to customize servers
   - The example uses `host.docker.internal` for Docker compatibility
   - Change to `localhost` if running outside Docker

3. Restart the container:
```bash
docker compose restart
```

## API Endpoints

- `POST /chat` - Send a message, get a response
- `GET /model` - Get current model
- `POST /model` - Change model
- `GET /conversation` - Get conversation history
- `DELETE /conversation` - Clear context

## Configuration

Environment variables:
- `DEFAULT_MODEL` - Default model to use (default: `ollama:qwen2.5:14b`)
- `MCP_CONFIG_FILE` - Path to MCP servers config file (default: `/app/mcp_config.json` in Docker)
- `MCP_SERVERS` - Comma-separated list of servers to enable (optional)

See [docs/mcp_configuration.md](docs/mcp_configuration.md) for detailed MCP setup.