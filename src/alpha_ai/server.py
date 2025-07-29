"""FastAPI server for Alpha AI."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from alpha_ai.models import (
    ChatRequest, ChatResponse, ModelInfo, 
    ModelChangeRequest, ConversationResponse, ChatMessage,
    ToolCall, ToolReturn
)
from pydantic_ai.messages import (
    ModelResponse, ModelRequest, ToolCallPart, ToolReturnPart
)
from alpha_ai.settings import settings
from alpha_ai.agent import agent_manager


# Global state (will be replaced with proper persistence)
conversation = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting Alpha AI server...")
    print(f"Default model: {settings.default_model}")
    if settings.mcp_config_file:
        print(f"MCP config file: {settings.mcp_config_file}")
        if settings.mcp_servers:
            print(f"Enabled MCP servers: {', '.join(settings.mcp_servers)}")
    
    # Initialize the agent
    await agent_manager.initialize()
    print("Agent initialized successfully")
    
    yield
    
    # Shutdown
    print("Shutting down Alpha AI server...")
    await agent_manager.cleanup()


app = FastAPI(
    title="Alpha AI",
    description="Provider-agnostic AI agent server",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the web UI."""
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "Alpha AI API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": agent_manager.get_current_model(),
        "mcp_servers": list(agent_manager.mcp_servers.keys())
    }


@app.post(f"{settings.api_v1_prefix}/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and get a response."""
    global conversation
    
    # Add user message to conversation
    conversation.append({
        "role": "user",
        "content": request.message
    })
    
    # Generate AI response and get full result
    result = await agent_manager.chat_with_result(request.message, conversation)
    response_text = result.output
    
    # Add assistant response to conversation
    conversation.append({
        "role": "assistant",
        "content": response_text
    })
    
    # Extract tool calls from message history
    tool_calls = []
    messages = result.new_messages()
    
    # Find tool calls and their returns
    tool_call_map = {}
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    tool_call = ToolCall(
                        tool_name=part.tool_name,
                        args=part.args if isinstance(part.args, dict) else {},
                        tool_call_id=part.tool_call_id
                    )
                    tool_call_map[part.tool_call_id] = tool_call
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    if part.tool_call_id in tool_call_map:
                        tool_return = ToolReturn(
                            tool_name=part.tool_name,
                            content=str(part.content),
                            tool_call_id=part.tool_call_id
                        )
                        tool_calls.append((tool_call_map[part.tool_call_id], tool_return))
    
    return ChatResponse(
        response=response_text,
        model=agent_manager.get_current_model(),
        usage={
            "request_tokens": len(request.message.split()),
            "response_tokens": len(response_text.split()),
            "total_tokens": len(request.message.split()) + len(response_text.split())
        },
        tool_calls=tool_calls if tool_calls else None
    )


@app.get(f"{settings.api_v1_prefix}/model", response_model=ModelInfo)
async def get_model():
    """Get the current model."""
    return ModelInfo(model=agent_manager.get_current_model())


@app.post(f"{settings.api_v1_prefix}/model", response_model=ModelInfo)
async def set_model(request: ModelChangeRequest):
    """Change the current model."""
    await agent_manager.change_model(request.model)
    return ModelInfo(model=agent_manager.get_current_model())


@app.get(f"{settings.api_v1_prefix}/conversation", response_model=ConversationResponse)
async def get_conversation(limit: int = 10):
    """Get the conversation history."""
    messages = conversation[-limit:] if len(conversation) > limit else conversation
    
    return ConversationResponse(
        messages=[
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp", datetime.now(timezone.utc))
            ) for msg in messages
        ],
        total_messages=len(conversation),
        model=agent_manager.get_current_model()
    )


@app.delete(f"{settings.api_v1_prefix}/conversation")
async def clear_conversation():
    """Clear the conversation context."""
    global conversation
    conversation = []
    
    return {"status": "conversation cleared", "model": agent_manager.get_current_model()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)