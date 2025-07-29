#!/usr/bin/env just --justfile

# List available commands
default:
    @just --list

# Install all dependencies
install:
    uv sync

# Run the API server locally
run-api:
    uv run --package alpha-ai python -m alpha_ai

# Run the MCP bridge
run-mcp:
    uv run --package alpha-ai-mcp python -m alpha_ai_mcp


# Build Docker image
build:
    docker compose build

# Start the stack
up:
    docker compose up -d

# Stop the stack
down:
    docker compose down

# View logs
logs:
    docker compose logs -f

# Run tests
test:
    uv run pytest

# Format code
format:
    uv run ruff format .

# Lint code
lint:
    uv run ruff check .

# Type check
typecheck:
    uv run mypy src/