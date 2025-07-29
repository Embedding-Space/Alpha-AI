"""PydanticAI agent management for Alpha AI."""

from typing import Optional, Dict, Any
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.openai import OpenAIProvider

from .settings import settings


class AlphaAgent:
    """Manages the PydanticAI agent for Alpha AI."""
    
    def __init__(self):
        self.current_model: str = settings.default_model
        self.agent: Optional[Agent] = None
        self.system_prompt = self._load_system_prompt()
        self._create_agent()
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt for Alpha."""
        # For now, a simple prompt. Later we can load from file or Alpha Brain
        return """You are Alpha AI, a helpful AI assistant.
        
You have access to conversation history and can maintain context across messages.
Respond helpfully and concisely to user queries."""
    
    def _parse_model_string(self, model: str) -> tuple[str, str]:
        """Parse model string like 'ollama:qwen2.5:14b' into provider and model."""
        parts = model.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid model format: {model}. Expected 'provider:model'")
        return parts[0], parts[1]
    
    def _create_agent(self):
        """Create a new PydanticAI agent with the current model."""
        provider, model_name = self._parse_model_string(self.current_model)
        
        # Map provider strings to PydanticAI model configurations
        if provider == "openai":
            model = OpenAIModel(model_name)
            self.agent = Agent(
                model=model,
                system_prompt=self.system_prompt
            )
        elif provider == "anthropic":
            model = AnthropicModel(model_name)
            self.agent = Agent(
                model=model,
                system_prompt=self.system_prompt
            )
        elif provider == "ollama":
            # For Ollama, we need to specify the base URL
            ollama_provider = OpenAIProvider(
                base_url=settings.ollama_base_url,
                api_key="ollama",  # Ollama doesn't need a real key
            )
            model = OpenAIModel(model_name, provider=ollama_provider)
            self.agent = Agent(
                model=model,
                system_prompt=self.system_prompt
            )
        elif provider == "groq":
            model = GroqModel(model_name)
            self.agent = Agent(
                model=model,
                system_prompt=self.system_prompt
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def chat(self, message: str, conversation: list[Dict[str, Any]]) -> str:  # noqa: ARG002
        """Generate a response to a user message."""
        if not self.agent:
            raise RuntimeError("Agent not initialized")
        
        # Convert conversation history to format PydanticAI expects
        # For now, we'll just use the current message
        # TODO: Implement proper conversation context
        
        try:
            result = await self.agent.run(message)
            # PydanticAI returns the response as output for simple agents
            return str(result.output) if result.output else "I couldn't generate a response."
        except UnexpectedModelBehavior as e:
            # Handle cases where model doesn't respond as expected
            return f"I encountered an error: {str(e)}. Please try again."
        except Exception as e:
            # Handle other errors
            return f"An error occurred: {str(e)}"
    
    def change_model(self, new_model: str):
        """Change the current model and recreate the agent."""
        self.current_model = new_model
        self._create_agent()
    
    def get_current_model(self) -> str:
        """Get the current model string."""
        return self.current_model


# Global agent instance
agent_manager = AlphaAgent()