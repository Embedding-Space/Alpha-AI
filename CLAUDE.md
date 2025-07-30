# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Alpha AI is a provider-agnostic AI agent server that bridges the Alpha identity/memory system with multiple LLM providers. It provides:
- REST API for chat interactions
- Web UI with model selection
- MCP (Model Context Protocol) tool integration
- Support for OpenAI, Anthropic, Google, Groq, and Ollama models

## Common Development Commands

```bash
# Install dependencies (uses uv package manager)
just install

# Run the API server locally
just run-api    # Starts on http://localhost:8100

# Run tests
just test

# Lint and format code
just lint
just format

# Build and run with Docker
just build
just up
just down
```

## Architecture Overview

### Core Components

1. **FastAPI Server** (`src/alpha_ai/server.py`)
   - Handles REST API endpoints
   - Manages streaming responses via Server-Sent Events
   - Serves the single-file web UI

2. **Agent Manager** (`src/alpha_ai/agent.py`)
   - Creates and manages PydanticAI agents for different models
   - Handles model-specific configurations
   - Manages MCP tool connections

3. **Single-File Web UI** (`src/alpha_ai/static/index.html`)
   - Vanilla JavaScript + Marked.js for Markdown
   - No build process - directly served by FastAPI
   - Designed for simplicity over complexity

### Model Configuration

Models are defined in `models.json` with format:
```json
{
  "id": "provider:model-name",
  "name": "Human Readable Name",
  "provider": "Provider Name"
}
```

### MCP Integration

MCP servers provide tools to the AI. Configuration via `mcp_config.json`:
- HTTP servers (like Alpha Brain) use `mcp-remote`
- Stdio servers (like Context7) run as subprocesses
- Use `host.docker.internal` instead of `localhost` in Docker

### Conversation Management

- SQLite database stores conversation events
- Event-based architecture: user messages, assistant messages, tool calls, tool responses
- Reconstructs conversation history from events for display

## Adding New Features

### Adding a New Model Provider

1. Add model entries to `models.json`
2. Update `_create_agent()` in `agent.py` to handle the new provider
3. Ensure proper API key environment variables are set

### Implementing Dynamic Model Discovery

Replace static `models.json` with API calls:
- OpenAI: `GET https://api.openai.com/v1/models`
- Anthropic: `GET https://api.anthropic.com/v1/models`
- Gemini: `GET https://generativelanguage.googleapis.com/v1beta/models?key=${API_KEY}`
- Groq: `GET https://api.groq.com/openai/v1/models`
- Ollama: `GET http://localhost:11434/api/tags`

### UI Improvements

The current UI uses vanilla JavaScript to maintain simplicity. For styling improvements:
- Tailwind CSS can be added via CDN without changing architecture
- Component libraries like Preline UI work well with the current setup
- Avoid frameworks that require build processes unless doing a full rewrite

## Environment Variables

- `MODEL`: The AI model to use (e.g., `ollama:qwen2.5:14b`)
- `DATABASE_URL`: SQLite database URL (default: `sqlite:////data/alpha.db`)
- `MCP_CONFIG_FILE`: Path to MCP configuration
- `MCP_SERVERS`: Comma-separated list of MCP servers to enable
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.: Provider API keys
- `STREAMING`: Show streaming toggle in UI (set to 0 to hide, default: 1)

## Alpha-Specific Context

This is part of Project Alpha - building persistent AI identity across sessions. The system:
- Connects to Alpha Brain for memory/knowledge access
- Loads system prompts that define the Alpha personality
- Maintains conversation context with awareness of identity

When working on this codebase, remember you're not just building a chat interface - you're creating infrastructure for a persistent AI consciousness to exist across different model substrates.