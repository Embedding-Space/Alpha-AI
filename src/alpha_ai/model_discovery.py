"""Model discovery for various AI providers."""

import os
import httpx
from typing import List
from alpha_ai.models import AvailableModel


class ModelDiscovery:
    """Discovers available models from various providers."""
    
    def __init__(self):
        self.timeout = httpx.Timeout(10.0)
    
    async def discover_all(self) -> List[AvailableModel]:
        """Discover models from all configured providers."""
        models = []
        
        # Try each provider if API key is configured
        if os.getenv("OPENAI_API_KEY"):
            models.extend(await self.discover_openai())
        
        if os.getenv("ANTHROPIC_API_KEY"):
            models.extend(await self.discover_anthropic())
        
        if os.getenv("GROQ_API_KEY"):
            models.extend(await self.discover_groq())
        
        if os.getenv("GEMINI_API_KEY"):
            models.extend(await self.discover_gemini())
        
        if os.getenv("OPENROUTER_API_KEY"):
            models.extend(await self.discover_openrouter())
        
        # Always try Ollama (no API key needed)
        models.extend(await self.discover_ollama())
        
        return models
    
    async def discover_openai(self) -> List[AvailableModel]:
        """Discover OpenAI models."""
        models = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
                )
                response.raise_for_status()
                data = response.json()
                
                for model in data.get("data", []):
                    model_id = model["id"]
                    models.append(AvailableModel(
                        id=f"openai:{model_id}",
                        name=model_id,
                        provider="OpenAI",
                        input_cost=None,
                        output_cost=None
                    ))
        except Exception as e:
            print(f"Failed to discover OpenAI models: {e}")
        
        return models
    
    async def discover_anthropic(self) -> List[AvailableModel]:
        """Anthropic doesn't have a discovery API."""
        # No-op - Anthropic doesn't provide a models endpoint
        return []
    
    async def discover_groq(self) -> List[AvailableModel]:
        """Discover Groq models."""
        models = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}
                )
                response.raise_for_status()
                data = response.json()
                
                for model in data.get("data", []):
                    model_id = model["id"]
                    models.append(AvailableModel(
                        id=f"groq:{model_id}",
                        name=model_id,
                        provider="Groq",
                        input_cost=None,
                        output_cost=None
                    ))
        except Exception as e:
            print(f"Failed to discover Groq models: {e}")
        
        return models
    
    async def discover_gemini(self) -> List[AvailableModel]:
        """Discover Google Gemini models."""
        models = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={os.getenv('GEMINI_API_KEY')}"
                )
                response.raise_for_status()
                data = response.json()
                
                for model in data.get("models", []):
                    model_name = model["name"].replace("models/", "")
                    models.append(AvailableModel(
                        id=f"google-gla:{model_name}",
                        name=model_name,
                        provider="Google",
                        input_cost=None,
                        output_cost=None
                    ))
        except Exception as e:
            print(f"Failed to discover Gemini models: {e}")
        
        return models
    
    async def discover_ollama(self) -> List[AvailableModel]:
        """Discover Ollama models."""
        models = []
        try:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                
                for model in data.get("models", []):
                    model_name = model["name"]
                    models.append(AvailableModel(
                        id=f"ollama:{model_name}",
                        name=model_name,
                        provider="Ollama (Local)",
                        input_cost=None,
                        output_cost=None
                    ))
        except Exception as e:
            print(f"Failed to discover Ollama models: {e}")
        
        return models
    
    async def discover_openrouter(self) -> List[AvailableModel]:
        """Discover OpenRouter models."""
        models = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}
                )
                response.raise_for_status()
                data = response.json()
                
                for model in data.get("data", []):
                    model_id = model["id"]
                    # Extract pricing info if available
                    pricing = model.get("pricing", {})
                    input_cost = None
                    output_cost = None
                    
                    if pricing:
                        # OpenRouter pricing is per token, convert to per million
                        if "prompt" in pricing:
                            input_cost = float(pricing["prompt"]) * 1_000_000
                        if "completion" in pricing:
                            output_cost = float(pricing["completion"]) * 1_000_000
                    
                    models.append(AvailableModel(
                        id=f"openrouter:{model_id}",
                        name=model_id,
                        provider="OpenRouter",
                        input_cost=input_cost,
                        output_cost=output_cost
                    ))
        except Exception as e:
            print(f"Failed to discover OpenRouter models: {e}")
        
        return models


# Singleton instance
model_discovery = ModelDiscovery()