"""FastAPI server for Alpha AI."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alpha_ai.models import (
    ChatRequest, ChatResponse, ModelInfo, 
    ModelChangeRequest, ConversationResponse, ChatMessage
)
from alpha_ai.settings import settings


# Global state (will be replaced with proper persistence)
current_model = settings.default_model
conversation = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting Alpha AI server...")
    print(f"Default model: {settings.default_model}")
    if settings.alpha_brain_url:
        print(f"Alpha Brain URL: {settings.alpha_brain_url}")
    
    yield
    
    # Shutdown
    print("Shutting down Alpha AI server...")


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": current_model,
        "alpha_brain_connected": settings.alpha_brain_url is not None
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
    
    # TODO: Implement actual AI response generation
    # For now, return a mock response
    response_text = f"I received your message: '{request.message}'. (Using model: {current_model})"
    
    # Add assistant response to conversation
    conversation.append({
        "role": "assistant",
        "content": response_text
    })
    
    return ChatResponse(
        response=response_text,
        model=current_model,
        usage={
            "request_tokens": len(request.message.split()),
            "response_tokens": len(response_text.split()),
            "total_tokens": len(request.message.split()) + len(response_text.split())
        }
    )


@app.get(f"{settings.api_v1_prefix}/model", response_model=ModelInfo)
async def get_model():
    """Get the current model."""
    return ModelInfo(model=current_model)


@app.post(f"{settings.api_v1_prefix}/model", response_model=ModelInfo)
async def set_model(request: ModelChangeRequest):
    """Change the current model."""
    global current_model
    
    # TODO: Validate model is available
    current_model = request.model
    
    return ModelInfo(model=current_model)


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
        model=current_model
    )


@app.delete(f"{settings.api_v1_prefix}/conversation")
async def clear_conversation():
    """Clear the conversation context."""
    global conversation
    conversation = []
    
    return {"status": "conversation cleared", "model": current_model}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)