"""Pydantic models for Alpha AI API."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: str = Field(description="Role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(description="The user's message")


class ToolCall(BaseModel):
    """A tool call made by the model."""
    tool_name: str = Field(description="Name of the tool called")
    args: Dict[str, Any] = Field(description="Arguments passed to the tool")
    tool_call_id: str = Field(description="Unique identifier for the tool call")


class ToolReturn(BaseModel):
    """The return value from a tool call."""
    tool_name: str = Field(description="Name of the tool that returned")
    content: str = Field(description="Tool return content")
    tool_call_id: str = Field(description="Unique identifier matching the tool call")


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    response: str = Field(description="The assistant's response")
    model: str = Field(description="Model used for generation")
    usage: dict = Field(description="Token usage statistics")
    tool_calls: Optional[List[tuple[ToolCall, ToolReturn]]] = Field(
        default=None, 
        description="Tool calls made during this interaction"
    )


class ModelInfo(BaseModel):
    """Current model information."""
    model: str = Field(description="Current model identifier")


class ModelChangeRequest(BaseModel):
    """Request to change the model."""
    model: str = Field(description="New model identifier")


class MessageWithToolCalls(BaseModel):
    """A message with optional tool calls."""
    role: str = Field(description="Role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tool_calls: Optional[List[tuple[ToolCall, Optional[ToolReturn]]]] = Field(
        default=None,
        description="Tool calls made during this message"
    )


class ConversationResponse(BaseModel):
    """Conversation history response."""
    messages: List[MessageWithToolCalls] = Field(description="Recent messages with tool calls")
    total_messages: int = Field(description="Total messages in conversation")
    model: str = Field(description="Current model")