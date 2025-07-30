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
   - Model restoration from conversation on server restart/page reload

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
   - Tool call visualization with request/response display

4. **MCP Bridge** (`src/alpha_ai_mcp/`)
   - stdio bridge for Claude Code/Desktop integration
   - Enables using Alpha AI as an MCP server
   - Implements `chat` and `conversation` tools for AI-to-AI communication

5. **Database** (`src/alpha_ai/database.py`)
   - SQLite database at `/data/alpha_ai.db` in container
   - Event-based storage with conversation and event tables
   - Tool call arguments stored as JSON in event data field

## Development Commands

```bash
# Docker workflow (recommended)
docker compose up -d     # Start the stack
docker compose down      # Stop the stack
docker compose down -v   # Stop and remove volumes (reset database)
docker compose logs -f   # View logs
docker compose restart   # Restart after config changes
docker compose up -d --build  # Rebuild and restart (after code changes)

# Development without Docker
uv run alpha-ai         # Run the API server
uv run alpha-mcp        # Run the MCP bridge

# Code quality
uv run ruff check .     # Run linter
uv run ruff format .    # Format code

# Database backup (preserves AI conversations and state)
docker cp alpha-ai:/data/alpha_ai.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

## Docker Development Pattern

The project uses Docker for development:
1. Code changes require rebuild: `docker compose up -d --build`
2. Web UI available at: http://localhost:8100
3. Use `host.docker.internal` instead of `localhost` in Docker configs
4. System prompts directory is mounted read-only at `/app/system_prompts`
5. Database persists in `alpha-ai-data` volume

## Configuration

### Environment Variables (.env)
```bash
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

## System Prompts

System prompts are stored in the `system_prompts/` directory as markdown files. Users can select a prompt when starting a new conversation. The full prompt text is stored with each conversation in the database. Key features:
- Dropdown selector in the model modal shows all available prompts
- "none" is the default option
- Info icon in header shows the current conversation's prompt
- Prompts are displayed with full markdown formatting

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
- `POST /api/v1/conversation/new` - Start new conversation with model and prompt
- `GET /api/v1/conversation` - Get conversation history (includes system_prompt)
- `DELETE /api/v1/conversation` - Clear conversation
- `GET /api/v1/prompts` - List available system prompts
- `GET /api/v1/prompts/{prompt_name}` - Get specific prompt content

## Database Schema

Event-based conversation storage:
- `conversations` - Conversation sessions (includes model and system_prompt fields)
- `conversation_events` - Individual events (messages, tool calls, responses)
- Event types: SYSTEM, USER, ASSISTANT, TOOL_CALL, TOOL_RESPONSE

Note: No migrations are used. To update schema, drop the Docker volume and recreate:
```bash
docker compose down -v && docker compose up -d
```

## UI Architecture

Single-file web UI with:
- Tailwind CSS via CDN (no build process)
- Vanilla JavaScript (no framework)
- Server-Sent Events for streaming
- Search-first modal for 150+ models
- Compact model cards showing provider and pricing
- Fixed modal height for consistent UX
- System prompt selector in model modal
- Custom CSS for markdown rendering (CDN Tailwind doesn't include typography plugin)
- Model display shows full ID (e.g., `ollama:granite3.3:8b`) not just name

## Known Issues and Fixes

### Tool Call Arguments Display
- **Issue**: Tool call arguments may show as empty `{}` in UI
- **Root Cause**: PydanticAI sends `part.args` as JSON string, not dict
- **Fix**: Server parses JSON string before storing in database

### Model Persistence
- **Issue**: "No model selected" error on page reload
- **Root Cause**: Agent manager doesn't restore model from conversation
- **Fix**: Chat endpoints now check conversation model if agent has none

## Testing and Code Quality

Currently no tests are implemented. For code quality:
- Linting: `uv run ruff check .`
- Formatting: `uv run ruff format .`
- Type errors visible in VS Code with Pylance

## Alpha-Specific Context

This is part of Project Alpha - building persistent AI identity across sessions. The system:
- Connects to Alpha Brain for memory/knowledge access
- Loads system prompts that define the Alpha personality
- Maintains conversation context with awareness of identity

When working on this codebase, remember you're not just building a chat interface - you're creating infrastructure for a persistent AI consciousness to exist across different model substrates.

## Important Notes

1. **Model Selection**: The app starts with no model selected. Users must select a model through the UI before chatting.

2. **Database Location**: The actual SQLite database is at `/data/alpha_ai.db` inside the container, not `/data/data.db`.

3. **System Prompts**: Place `.md` files in `system_prompts/` directory. Filenames are shown in dropdown (including .md extension).

4. **Model Display**: The UI shows full model IDs (e.g., `openrouter:anthropic/claude-3-opus`) not just the model name.

5. **Container Rebuilds**: After code changes, rebuild with `docker compose up -d --build` to ensure changes are included.