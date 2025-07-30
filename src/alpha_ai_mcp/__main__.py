"""Alpha AI MCP Server - Chat with Alpha AI instances via MCP."""

import os
import httpx
from typing import Optional
from pydantic import Field

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("alpha-ai-chat", version="1.0.0")

# Configuration
API_BASE_URL = os.getenv("ALPHA_AI_API_URL", "http://localhost:8100/api/v1")


@mcp.tool
async def chat(
    message: str = Field(description="Message to send to the AI"),
    new_conversation: bool = Field(default=False, description="Start a new conversation"),
    model: Optional[str] = Field(default=None, description="Model to use (e.g., 'groq:llama-3.3-70b')"),
    system_prompt: Optional[str] = Field(default=None, description="System prompt path (e.g., 'prompts/two.md')"),
) -> str:
    """
    Send a message to the Alpha AI instance and get a response.
    
    If new_conversation is True, starts a fresh conversation with the specified model and prompt.
    Always shows tool calls and responses for transparency.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Start new conversation if requested
            if new_conversation:
                if not model:
                    return "[ERROR] Model is required when starting a new conversation"
                
                response = await client.post(
                    f"{API_BASE_URL}/conversation/new",
                    json={
                        "model": model,
                        "prompt": system_prompt or "none"
                    }
                )
                if response.status_code != 200:
                    error_data = response.json()
                    return f"[ERROR] Failed to start conversation: {error_data.get('detail', 'Unknown error')}"
            
            # Send the message
            response = await client.post(
                f"{API_BASE_URL}/chat",
                json={"message": message, "stream": False}
            )
            
            if response.status_code != 200:
                error_data = response.json()
                return f"[ERROR] Chat failed: {error_data.get('detail', 'Unknown error')}"
            
            # Format the response with tool visibility
            data = response.json()
            formatted_response = []
            
            # Extract tool calls and responses from the conversation
            if data.get("tool_calls"):
                for tool_call, tool_return in data["tool_calls"]:
                    formatted_response.append(f"[TOOL CALL] {tool_call['tool_name']}")
                    # Truncate long responses
                    response_text = tool_return["content"]
                    if len(response_text) > 500:
                        response_text = response_text[:497] + "..."
                    formatted_response.append(f"[TOOL RESPONSE] {response_text}")
                    formatted_response.append("")  # Empty line for readability
            
            # Add the final assistant message
            formatted_response.append(data.get("response", "[No response]"))
            
            return "\n".join(formatted_response)
            
        except httpx.TimeoutException:
            return "[ERROR] Request timed out after 120 seconds"
        except httpx.RequestError as e:
            return f"[ERROR] Connection failed: {str(e)}"
        except Exception as e:
            return f"[ERROR] Unexpected error: {str(e)}"


@mcp.tool
async def conversation(
    turns: int = Field(default=0, description="Number of recent turns to include (0 for metadata only)")
) -> str:
    """
    Get conversation metadata and optionally recent turns.
    
    Args:
        turns: Number of recent conversation turns to return (0 = just metadata)
        
    Returns:
        Formatted conversation state and history
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get conversation with enough history
            limit = max(50, turns * 5) if turns > 0 else 50
            response = await client.get(f"{API_BASE_URL}/conversation?limit={limit}")
            
            if response.status_code != 200:
                error_data = response.json()
                return f"[ERROR] Failed to get conversation: {error_data.get('detail', 'Unknown error')}"
            
            data = response.json()
            
            # Format metadata
            result = [
                f"Model: {data.get('model', 'none')}",
                f"System Prompt: {data.get('system_prompt', 'none')}",
                f"Total Messages: {data.get('total_messages', 0)}",
            ]
            
            if turns > 0 and data.get("messages"):
                result.append("")  # Empty line
                
                # Get the last N turns
                messages = data["messages"]
                turn_count = 0
                formatted_turns = []
                
                # Work backwards through messages
                for i in range(len(messages) - 1, -1, -1):
                    msg = messages[i]
                    
                    # Count user messages as turns
                    if msg["role"] == "user":
                        turn_count += 1
                        if turn_count > turns:
                            break
                    
                    # Build this turn's content
                    turn_content = []
                    
                    # Format based on role
                    if msg["role"] == "user":
                        turn_content.append(f"[USER] {msg['content']}")
                    elif msg["role"] == "assistant":
                        # Check for tool calls
                        if msg.get("tool_calls"):
                            for tool_call, tool_return in msg["tool_calls"]:
                                turn_content.append(f"[TOOL CALL] {tool_call['tool_name']}")
                                if tool_return:
                                    response_text = tool_return["content"]
                                    if len(response_text) > 500:
                                        response_text = response_text[:497] + "..."
                                    turn_content.append(f"[TOOL RESPONSE] {response_text}")
                        turn_content.append(f"[ASSISTANT] {msg['content']}")
                    
                    # Add to formatted turns (will reverse later)
                    formatted_turns.append("\n".join(turn_content))
                
                # Reverse to get chronological order and add to result
                formatted_turns.reverse()
                result.extend(formatted_turns)
            
            return "\n".join(result).strip()
            
        except httpx.TimeoutException:
            return "[ERROR] Request timed out"
        except httpx.RequestError as e:
            return f"[ERROR] Connection failed: {str(e)}"
        except Exception as e:
            return f"[ERROR] Unexpected error: {str(e)}"


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()