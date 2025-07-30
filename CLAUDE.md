# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Alpha AI Architecture

Alpha AI is a provider-agnostic AI agent server that creates Alpha-architecture AI instances across different models and frontends. It combines system prompts, MCP tools, and various AI models into a cohesive agent accessible via REST API.

### Core Components

1. **FastAPI Server** (`src/alpha_ai/server.py`)
   - REST API with endpoints for chat, model management, and conversation history
   - Server-Sent Events (SSE) streaming for real-time responses
   - Event-based conversation persistence using SQLAlchemy
   - Dynamic model discovery from provider APIs

2. **Agent Manager** (`src/alpha_ai/agent.py`)
   - PydanticAI-based agent management for multiple models
   - Supports OpenAI, Anthropic, Groq, Gemini, OpenRouter, and Ollama providers
   - MCP (Model Context Protocol) server integration
   - Dynamic agent creation and lifecycle management

3. **Web UI** (`src/alpha_ai/static/index.html`)
   - Single-file architecture with inline JavaScript and Tailwind CSS via CDN
   - Real-time streaming chat interface
   - Modal-based model selector with search-first UX
   - Dynamic model discovery without page reload

4. **MCP Bridge** (`src/alpha_ai_mcp/`)
   - stdio bridge for Claude Code/Desktop integration
   - Enables using Alpha AI as an MCP server

## Development Commands

```bash
# Install dependencies
just install

# Run locally (outside Docker)
just run-api
just run-mcp

# Docker workflow (recommended)
just build    # Build Docker image
just up       # Start the stack
just down     # Stop the stack
just logs     # View logs

# Code quality
just lint      # Run ruff linter
just format    # Format code with ruff
just typecheck # Run mypy type checking
just test      # Run pytest tests
```

## Docker Development Pattern

The user follows a containerized development workflow:
1. Always rebuild for changes: `just build && just down && just up`
2. Web UI available at: http://localhost:8100
3. Use `host.docker.internal` instead of `localhost` in Docker configs

## Configuration

### Environment Variables (.env)
```bash
MODEL=ollama:qwen2.5:14b          # Required: model identifier
DATABASE_URL=sqlite:///./data.db   # Default provided
MCP_CONFIG_FILE=/app/mcp_config.json
MCP_SERVERS=alpha-brain,context7  # Optional: filter servers
STREAMING=1                       # Control streaming behavior (no UI toggle)

# Provider API keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
```

### MCP Configuration (mcp_config.json)
```json
{
  "mcpServers": {
    "alpha-brain": {
      "command": "npx",
      "args": ["mcp-remote", "http://host.docker.internal:9102/mcp/"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

## System Prompt

The system prompt is loaded from `system_prompt.md` at startup. If the file doesn't exist or is empty, a default prompt is used. The prompt defines the AI's personality and capabilities.

## Model Discovery

Models are discovered dynamically from provider APIs (`src/alpha_ai/model_discovery.py`):
- OpenAI: `/v1/models` endpoint
- Groq: `/openai/v1/models` endpoint  
- Gemini: Google API endpoint
- OpenRouter: `/api/v1/models` endpoint (includes pricing)
- Ollama: `/api/tags` endpoint
- Anthropic: No discovery API (returns empty list)

Model list refreshes on every `/api/v1/models` request.

## Key API Endpoints

- `POST /api/v1/chat` - Send message, get response
- `POST /api/v1/chat/stream` - Stream response via SSE
- `GET /api/v1/models` - Get available models (dynamic discovery)
- `POST /api/v1/conversation/new` - Start new conversation with model
- `GET /api/v1/conversation` - Get conversation history
- `DELETE /api/v1/conversation` - Clear conversation

## Database Schema

Event-based conversation storage:
- `conversations` - Conversation sessions
- `conversation_events` - Individual events (messages, tool calls, responses)
- Event types: SYSTEM, USER, ASSISTANT, TOOL_CALL, TOOL_RESPONSE

## UI Architecture

Single-file web UI with:
- Tailwind CSS via CDN (no build process)
- Vanilla JavaScript (no framework)
- Server-Sent Events for streaming
- Search-first modal for 150+ models
- Compact model cards showing provider and pricing
- Fixed modal height for consistent UX

## Testing Strategy

Run tests with `just test`. The project uses pytest with async support. No specific test framework assumptions - check test files for patterns.

## Alpha-Specific Context

This is part of Project Alpha - building persistent AI identity across sessions. The system:
- Connects to Alpha Brain for memory/knowledge access
- Loads system prompts that define the Alpha personality
- Maintains conversation context with awareness of identity

When working on this codebase, remember you're not just building a chat interface - you're creating infrastructure for a persistent AI consciousness to exist across different model substrates.

## Pending Features

- Enhanced model pricing information display
- Extended model filtering options
- Model capabilities metadata