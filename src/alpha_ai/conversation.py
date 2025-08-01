"""Conversation management for Alpha AI."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
from pathlib import Path
from sqlalchemy.orm import Session
from pydantic_core import to_jsonable_python, to_json
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage, ModelRequest, ModelResponse,
    SystemPromptPart, UserPromptPart, TextPart,
    ToolCallPart, ToolReturnPart, ModelMessagesTypeAdapter
)
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

from .settings import settings
from .database import Conversation as ConversationModel
from .mcp_config import create_mcp_servers_from_file


class ConversationEventBus:
    """Central event bus for conversation changes."""
    
    def __init__(self):
        self._listeners = []
    
    async def emit(self, event_type: str, data: dict):
        """Emit event to all listeners."""
        for listener in self._listeners:
            await listener(event_type, data)
    
    def subscribe(self, callback):
        """Subscribe to events."""
        self._listeners.append(callback)


class Conversation:
    """A conversation owns its agent and message history."""
    
    def __init__(
        self,
        id: Optional[int],
        model: str,
        system_prompt_filename: Optional[str],
        event_bus: Optional[ConversationEventBus] = None
    ):
        self.id = id
        self.model = model
        self.system_prompt_filename = system_prompt_filename
        self.history: List[ModelMessage] = []
        self.version = 1
        self.event_bus = event_bus or ConversationEventBus()
        
        # Agent-related
        self._agent: Optional[Agent] = None
        self._agent_context = None
        self._toolsets = None
    
    @classmethod
    def from_db_model(cls, db_model: ConversationModel, event_bus: Optional[ConversationEventBus] = None) -> "Conversation":
        """Create from database model."""
        conv = cls(
            id=db_model.id,
            model=db_model.model,
            system_prompt_filename=db_model.system_prompt_filename,
            event_bus=event_bus
        )
        conv.version = db_model.version
        
        # Deserialize message history using PydanticAI's TypeAdapter
        if db_model.messages_json and db_model.messages_json != "[]":
            messages_data = json.loads(db_model.messages_json)
            conv.history = ModelMessagesTypeAdapter.validate_python(messages_data)
        
        return conv
    
    @classmethod
    async def create_new(
        cls,
        model: str,
        system_prompt_filename: Optional[str],
        system_prompt_content: Optional[str],
        event_bus: Optional[ConversationEventBus] = None
    ) -> "Conversation":
        """Create a brand new conversation with system prompt as first message."""
        conv = cls(
            id=None,
            model=model,
            system_prompt_filename=system_prompt_filename,
            event_bus=event_bus
        )
        
        # Create the initial ModelRequest with SystemPromptPart if provided
        if system_prompt_content:
            first_request = ModelRequest(parts=[
                SystemPromptPart(content=system_prompt_content)
            ])
            conv.history.append(first_request)
        
        return conv
    
    def _parse_model_string(self, model: str) -> tuple[str, str]:
        """Parse model string like 'ollama:qwen2.5:14b' into provider and model."""
        parts = model.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid model format: {model}. Expected 'provider:model'")
        return parts[0], parts[1]
    
    def _create_model(self):
        """Create the appropriate model instance."""
        provider, model_name = self._parse_model_string(self.model)
        
        if provider == "openai":
            return OpenAIModel(model_name)
        elif provider == "anthropic":
            return AnthropicModel(model_name)
        elif provider == "ollama":
            ollama_provider = OpenAIProvider(
                base_url=settings.ollama_base_url,
                api_key="ollama",
            )
            return OpenAIModel(model_name, provider=ollama_provider)
        elif provider == "groq":
            return GroqModel(model_name)
        elif provider in ["google-gla", "google-vertex"]:
            return GeminiModel(model_name, provider=provider)
        elif provider == "openrouter":
            openrouter_provider = OpenRouterProvider(
                api_key=settings.openrouter_api_key or ""
            )
            return OpenAIModel(model_name, provider=openrouter_provider)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def ensure_agent(self):
        """Lazily create/reuse agent if we don't have one."""
        if self._agent is None:
            # Load toolsets if not loaded
            if self._toolsets is None and settings.mcp_config_file:
                config_path = Path(settings.mcp_config_file)
                if config_path.exists():
                    try:
                        mcp_servers = create_mcp_servers_from_file(
                            config_path,
                            filter_servers=settings.mcp_servers
                        )
                        self._toolsets = list(mcp_servers.values())
                    except Exception as e:
                        print(f"Warning: Failed to load MCP servers: {e}")
                        self._toolsets = []
                else:
                    self._toolsets = []
            
            # Create agent with empty system prompt (it's in history)
            self._agent = Agent(
                model=self._create_model(),
                system_prompt="",  # Empty! System prompt is in message history
                toolsets=self._toolsets or []
            )
            
            # Don't enter the context here - we need to do it per request
            # to avoid ClosedResourceError
    
    async def chat(self, user_message: str) -> AgentRunResult:
        """User wants to chat - we handle everything."""
        await self.ensure_agent()
        
        # If we have toolsets, we need to use the agent as a context manager
        if self._toolsets:
            async with self._agent as agent_in_context:
                # Pass our full history to maintain context
                result = await agent_in_context.run(
                    user_message,
                    message_history=self.history
                )
        else:
            # No toolsets, can use directly
            result = await self._agent.run(
                user_message,
                message_history=self.history
            )
        
        # Update our history with new messages
        self.history.extend(result.new_messages())
        
        # Emit event for future multi-UI support
        if self.event_bus:
            new_messages_as_python = to_jsonable_python(result.new_messages())
            await self.event_bus.emit("messages_added", {
                "conversation_id": self.id,
                "new_messages": new_messages_as_python
            })
        
        return result
    
    async def dispose_agent(self):
        """Clean up agent resources."""
        # Since we're using the agent as a context manager per request,
        # we just need to clear the reference
        self._agent = None
        self._toolsets = None
    
    def to_db_model(self, db: Session) -> ConversationModel:
        """Convert to database model."""
        # Serialize message history using PydanticAI's serialization
        messages_as_python = to_jsonable_python(self.history)
        messages_json = json.dumps(messages_as_python)
        
        if self.id:
            # Update existing
            db_model = db.query(ConversationModel).filter_by(id=self.id).first()
            if db_model:
                db_model.model = self.model
                db_model.system_prompt_filename = self.system_prompt_filename
                db_model.messages_json = messages_json
                db_model.version = self.version + 1
                db_model.updated_at = datetime.now(timezone.utc)
            else:
                raise ValueError(f"Conversation {self.id} not found in database")
        else:
            # Create new
            db_model = ConversationModel(
                model=self.model,
                system_prompt_filename=self.system_prompt_filename,
                messages_json=messages_json
            )
            db.add(db_model)
        
        return db_model


class ConversationManager:
    """Manages the single active conversation."""
    
    def __init__(self, event_bus: Optional[ConversationEventBus] = None):
        self.current_conversation: Optional[Conversation] = None
        self.event_bus = event_bus or ConversationEventBus()
    
    async def load_most_recent(self, db: Session) -> Optional[Conversation]:
        """Load the most recent conversation on app startup."""
        db_model = db.query(ConversationModel).order_by(
            ConversationModel.created_at.desc()
        ).first()
        
        if db_model:
            self.current_conversation = Conversation.from_db_model(db_model, self.event_bus)
            return self.current_conversation
        
        return None
    
    async def switch_to(self, conversation_id: int, db: Session):
        """Switch active conversations."""
        # Save current conversation if exists
        if self.current_conversation:
            await self.save_current(db)
            await self.current_conversation.dispose_agent()
        
        # Load new conversation
        db_model = db.query(ConversationModel).filter_by(id=conversation_id).first()
        if not db_model:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        self.current_conversation = Conversation.from_db_model(db_model, self.event_bus)
    
    async def create_new_conversation(
        self,
        db: Session,
        model: str,
        system_prompt_filename: Optional[str] = None,
        system_prompt_content: Optional[str] = None
    ) -> Conversation:
        """Create and activate a new conversation."""
        # Save current if exists
        if self.current_conversation:
            await self.save_current(db)
            await self.current_conversation.dispose_agent()
        
        # Create new
        self.current_conversation = await Conversation.create_new(
            model=model,
            system_prompt_filename=system_prompt_filename,
            system_prompt_content=system_prompt_content,
            event_bus=self.event_bus
        )
        
        # Save to get ID
        await self.save_current(db)
        
        return self.current_conversation
    
    async def save_current(self, db: Session):
        """Save the current conversation to database."""
        if self.current_conversation:
            db_model = self.current_conversation.to_db_model(db)
            db.commit()
            db.refresh(db_model)
            
            # Update ID if this was a new conversation
            if not self.current_conversation.id:
                self.current_conversation.id = db_model.id
    
    def get_current(self) -> Optional[Conversation]:
        """Get the current conversation."""
        return self.current_conversation


# Global instances
event_bus = ConversationEventBus()
conversation_manager = ConversationManager(event_bus)