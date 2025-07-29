"""PydanticAI agent management for Alpha AI."""

from typing import Optional, Dict, Any
import httpx
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.mcp import MCPServerStreamableHTTP

from .settings import settings


class AlphaAgent:
    """Manages the PydanticAI agent for Alpha AI."""
    
    def __init__(self):
        self.current_model: str = settings.default_model
        self.agent: Optional[Agent] = None
        self.system_prompt = self._load_system_prompt()
        self.alpha_brain_server: Optional[MCPServerStreamableHTTP] = None
        self._agent_context = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the agent asynchronously."""
        if not self._initialized:
            await self._create_agent()
            self._initialized = True
    
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
    
    async def _create_agent(self):
        """Create a new PydanticAI agent with the current model."""
        # Clean up existing agent context if any
        if self._agent_context:
            try:
                await self.agent.__aexit__(None, None, None)
            except Exception:
                pass
            self._agent_context = None
            
        provider, model_name = self._parse_model_string(self.current_model)
        
        # Create Alpha Brain MCP client if URL is provided
        toolsets = []
        if settings.alpha_brain_url:
            self.alpha_brain_server = MCPServerStreamableHTTP(settings.alpha_brain_url)
            toolsets.append(self.alpha_brain_server)
            print(f"Alpha Brain MCP client configured for: {settings.alpha_brain_url}")
        
        # Map provider strings to PydanticAI model configurations
        if provider == "openai":
            model = OpenAIModel(model_name)
            self.agent = Agent(
                model=model,
                system_prompt=self.system_prompt,
                toolsets=toolsets
            )
        elif provider == "anthropic":
            model = AnthropicModel(model_name)
            self.agent = Agent(
                model=model,
                system_prompt=self.system_prompt,
                toolsets=toolsets
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
                system_prompt=self.system_prompt,
                toolsets=toolsets
            )
        elif provider == "groq":
            model = GroqModel(model_name)
            self.agent = Agent(
                model=model,
                system_prompt=self.system_prompt,
                toolsets=toolsets
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
            
        # Enter agent context to connect to MCP servers
        if self.agent and toolsets:
            try:
                self._agent_context = self.agent.__aenter__()
                await self._agent_context
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
                    print(f"\n❌ Unable to connect to MCP server at {settings.alpha_brain_url}")
                    print("   Application cannot start.\n")
                    print("   Possible solutions:")
                    print("   - Ensure Alpha Brain is running and accessible")
                    print("   - If running in Docker, use 'host.docker.internal' instead of 'localhost'")
                    print(f"     Example: {settings.alpha_brain_url.replace('localhost', 'host.docker.internal')}")
                    print("   - Clear the ALPHA_BRAIN_URL environment variable to start without Alpha Brain\n")
                    # Re-raise the original exception to terminate the app
                    raise
                # If we didn't find httpx.ConnectError, just re-raise
                raise
    
    async def chat(self, message: str, conversation: list[Dict[str, Any]]) -> str:  # noqa: ARG002
        """Generate a response to a user message."""
        # Ensure agent is initialized
        await self.initialize()
        
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
    
    async def change_model(self, new_model: str):
        """Change the current model and recreate the agent."""
        self.current_model = new_model
        await self._create_agent()
    
    def get_current_model(self) -> str:
        """Get the current model string."""
        return self.current_model
    
    async def cleanup(self):
        """Clean up resources."""
        if self._agent_context:
            try:
                await self.agent.__aexit__(None, None, None)
            except Exception:
                pass
            self._agent_context = None
        self.alpha_brain_server = None
        self.agent = None
        self._initialized = False


# Global agent instance
agent_manager = AlphaAgent()