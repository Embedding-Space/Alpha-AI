"""PydanticAI agent management for Alpha AI."""

from typing import Optional, Dict, Any
from pathlib import Path
import json
import httpx
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.openai import OpenAIProvider

from .settings import settings
from .mcp_config import create_mcp_servers_from_file
from .model_discovery import model_discovery
from .models import AvailableModel


class AlphaAgentManager:
    """Manages multiple PydanticAI agents for different models."""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.agent_contexts: Dict[str, Any] = {}
        self.current_model: str = settings.model
        self.system_prompt = self._load_system_prompt()
        self.mcp_servers: Dict[str, Any] = {}
        self.available_models: Dict[str, AvailableModel] = {}
        
    async def _load_available_models(self):
        """Discover available models from all providers."""
        try:
            models = await model_discovery.discover_all()
            self.available_models = {model.id: model for model in models}
            
            # Ensure the configured model is in the list (fallback)
            if settings.model not in self.available_models:
                parts = settings.model.split(":", 1)
                provider = parts[0].capitalize() if len(parts) > 1 else "Unknown"
                name = parts[1] if len(parts) > 1 else settings.model
                
                self.available_models[settings.model] = AvailableModel(
                    id=settings.model,
                    name=name,
                    provider=provider,
                    input_cost=None,
                    output_cost=None
                )
                
            print(f"Discovered {len(self.available_models)} models from providers")
            
        except Exception as e:
            print(f"Error discovering models: {e}")
            # Fallback to just the configured model
            parts = settings.model.split(":", 1)
            provider = parts[0].capitalize() if len(parts) > 1 else "Unknown"
            name = parts[1] if len(parts) > 1 else settings.model
            
            self.available_models = {
                settings.model: AvailableModel(
                    id=settings.model,
                    name=name,
                    provider=provider,
                    input_cost=None,
                    output_cost=None
                )
            }
    
    async def initialize(self):
        """Initialize the default agent."""
        # Load available models
        await self._load_available_models()
        
        # Load MCP servers once
        if not self.mcp_servers and settings.mcp_config_file:
            config_path = Path(settings.mcp_config_file)
            if config_path.exists():
                try:
                    self.mcp_servers = create_mcp_servers_from_file(
                        config_path,
                        filter_servers=settings.mcp_servers
                    )
                except Exception as e:
                    print(f"Warning: Failed to load MCP servers from {config_path}: {e}")
            else:
                print(f"Warning: MCP config file not found: {config_path}")
        
        # Initialize the default agent
        await self.get_or_create_agent(self.current_model)
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt from file or return empty string."""
        prompt_file = Path("system_prompt.md")
        if prompt_file.exists():
            try:
                return prompt_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Warning: Failed to read system_prompt.md: {e}")
                return ""
        
        # No file exists, return empty string
        return ""
    
    def _parse_model_string(self, model: str) -> tuple[str, str]:
        """Parse model string like 'ollama:qwen2.5:14b' into provider and model."""
        parts = model.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid model format: {model}. Expected 'provider:model'")
        return parts[0], parts[1]
    
    async def get_or_create_agent(self, model: str) -> Agent:
        """Get an existing agent or create a new one for the specified model."""
        if model in self.agents:
            return self.agents[model]
        
        # Create new agent
        await self._create_agent(model)
        return self.agents[model]
    
    async def _create_agent(self, model_string: str):
        """Create a new PydanticAI agent for the specified model."""
        provider, model_name = self._parse_model_string(model_string)
        
        # Get toolsets from MCP servers
        toolsets = list(self.mcp_servers.values())
        
        # Map provider strings to PydanticAI model configurations
        if provider == "openai":
            model = OpenAIModel(model_name)
        elif provider == "anthropic":
            model = AnthropicModel(model_name)
        elif provider == "ollama":
            # For Ollama, we need to specify the base URL
            ollama_provider = OpenAIProvider(
                base_url=settings.ollama_base_url,
                api_key="ollama",  # Ollama doesn't need a real key
            )
            model = OpenAIModel(model_name, provider=ollama_provider)
        elif provider == "groq":
            model = GroqModel(model_name)
        elif provider in ["google-gla", "google-vertex"]:
            model = GeminiModel(model_name, provider=provider)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        # Create the agent
        agent = Agent(
            model=model,
            system_prompt=self.system_prompt,
            toolsets=toolsets
        )
        
        # Enter agent context to connect to MCP servers
        if toolsets:
            try:
                # Store the agent context for proper cleanup
                self.agent_contexts[model_string] = await agent.__aenter__()
            except Exception as e:
                # Function to check if httpx.ConnectError is in the exception chain
                def find_connect_error(exc):
                    if isinstance(exc, httpx.ConnectError):
                        return True
                    # Handle ExceptionGroup (Python 3.11+)
                    if hasattr(exc, 'exceptions'):
                        for sub_exc in exc.exceptions:
                            if find_connect_error(sub_exc):
                                return True
                    # Check cause and context
                    if hasattr(exc, '__cause__') and exc.__cause__:
                        if find_connect_error(exc.__cause__):
                            return True
                    if hasattr(exc, '__context__') and exc.__context__:
                        if find_connect_error(exc.__context__):
                            return True
                    return False
                
                # Check if httpx.ConnectError is somewhere in the exception chain
                if find_connect_error(e):
                    print(f"\n❌ Unable to connect to MCP servers")
                    print("   Application cannot start.\n")
                    print("   Possible solutions:")
                    print("   - Ensure MCP servers are running and accessible")
                    print("   - If running in Docker, use 'host.docker.internal' instead of 'localhost'")
                    print("   - Check your mcp_config.json file for correct URLs\n")
                    # Re-raise the original exception to terminate the app
                    raise
                # If we didn't find httpx.ConnectError, just re-raise
                raise
        
        # Store the agent
        self.agents[model_string] = agent
    
    async def set_model(self, model: str):
        """Set the current model and ensure its agent exists."""
        if model not in self.available_models:
            raise ValueError(f"Model {model} not in available models")
        
        self.current_model = model
        await self.get_or_create_agent(model)
    
    async def chat(self, message: str, conversation: list[Dict[str, Any]]) -> str:  # noqa: ARG002
        """Generate a response to a user message using the current model."""
        result = await self.chat_with_result(message, conversation)
        return str(result.output) if result.output else "I couldn't generate a response."
    
    async def chat_with_result(self, message: str, conversation: list[Dict[str, Any]]) -> AgentRunResult:  # noqa: ARG002
        """Generate a response and return the full result with message history."""
        agent = await self.get_or_create_agent(self.current_model)
        
        # Convert conversation history to format PydanticAI expects
        # For now, we'll just use the current message
        # TODO: Implement proper conversation context
        
        try:
            result = await agent.run(message)
            return result
        except UnexpectedModelBehavior as e:
            # Handle cases where model doesn't respond as expected
            raise RuntimeError(f"I encountered an error: {str(e)}. Please try again.")
        except Exception as e:
            # Handle other errors
            raise RuntimeError(f"An error occurred: {str(e)}")
    
    @property
    def agent(self) -> Optional[Agent]:
        """Get the current agent for compatibility."""
        return self.agents.get(self.current_model)
    
    def get_model(self) -> str:
        """Get the current model string."""
        return self.current_model
    
    def get_available_models(self) -> Dict[str, AvailableModel]:
        """Get all available models."""
        return self.available_models
    
    async def cleanup(self):
        """Clean up all resources."""
        # Clean up all agent contexts
        for model_string, context in self.agent_contexts.items():
            if model_string in self.agents:
                try:
                    await self.agents[model_string].__aexit__(None, None, None)
                except Exception:
                    pass
        
        self.agent_contexts.clear()
        self.agents.clear()
        self.mcp_servers = {}


# Global agent manager instance
agent_manager = AlphaAgentManager()