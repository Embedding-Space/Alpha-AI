# Alpha-AI

Provider-agnostic AI agent server with REST API, MCP bridge, and terminal UI.

## Overview

Alpha-AI creates Alpha-architecture AI instances across different models and frontends. It combines system prompt + Alpha Brain tools + model into a cohesive Agent, exposing this via REST API.

## Components

- **alpha-ai**: Core REST API server (runs in Docker)
- **alpha-ai-mcp**: stdio MCP bridge for Claude Code/Desktop integration  
- **alpha-ai-tui**: Terminal UI client using Textual

## Quick Start

```bash
# Start the stack
docker compose up -d

# Run the terminal UI
uv run alpha-tui

# Use with Claude Code/Desktop via MCP
uv run alpha-mcp
```

## API Endpoints

- `POST /chat` - Send a message, get a response
- `GET /model` - Get current model
- `POST /model` - Change model
- `GET /conversation` - Get conversation history
- `DELETE /conversation` - Clear context

## Configuration

- `ALPHA_BRAIN_URL` - URL to Alpha Brain MCP server (optional)
- `DEFAULT_MODEL` - Default model to use (default: `ollama:qwen2.5:14b`)