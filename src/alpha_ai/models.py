"""Pydantic models for Alpha AI API."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: str = Field(description="Role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(description="The user's message")


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    response: str = Field(description="The assistant's response")
    model: str = Field(description="Model used for generation")
    usage: dict = Field(description="Token usage statistics")


class ModelInfo(BaseModel):
    """Current model information."""
    model: str = Field(description="Current model identifier")


class ModelChangeRequest(BaseModel):
    """Request to change the model."""
    model: str = Field(description="New model identifier")


class ConversationResponse(BaseModel):
    """Conversation history response."""
    messages: List[ChatMessage] = Field(description="Recent messages")
    total_messages: int = Field(description="Total messages in conversation")
    model: str = Field(description="Current model")