"""FastAPI server for Alpha AI."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from alpha_ai.models import (
    ChatRequest, ChatResponse, ModelInfo, 
    ConversationResponse, ChatMessage,
    ToolCall, ToolReturn
)
from pydantic_ai.messages import (
    ModelResponse, ModelRequest, ToolCallPart, ToolReturnPart,
    TextPart, TextPartDelta, ToolCallPartDelta,
    PartStartEvent, PartDeltaEvent, FinalResultEvent,
    FunctionToolCallEvent, FunctionToolResultEvent
)
from alpha_ai.settings import settings
from alpha_ai.agent import agent_manager
from pydantic_ai import Agent


# Global state (will be replaced with proper persistence)
conversation = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting Alpha AI server...")
    print(f"Model: {settings.model}")
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
        "model": agent_manager.get_model(),
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
        model=agent_manager.get_model(),
        usage={
            "request_tokens": len(request.message.split()),
            "response_tokens": len(response_text.split()),
            "total_tokens": len(request.message.split()) + len(response_text.split())
        },
        tool_calls=tool_calls if tool_calls else None
    )


@app.post(f"{settings.api_v1_prefix}/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream a response using Server-Sent Events with proper graph-based streaming."""
    global conversation
    
    # Add user message to conversation
    conversation.append({
        "role": "user",
        "content": request.message
    })
    
    async def generate():
        import json
        try:
            # Initialize agent if needed
            await agent_manager.initialize()
            
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'model': agent_manager.get_model()})}\n\n"
            
            # Track the full response text for conversation history
            full_response_parts = []
            
            # Use agent.iter() to walk through the execution graph
            async with agent_manager.agent.iter(request.message) as agent_run:
                async for node in agent_run:
                    
                    if Agent.is_user_prompt_node(node):
                        # Skip user prompt nodes - we already know what the user said
                        continue
                        
                    elif Agent.is_model_request_node(node):
                        # The model is generating a response - stream it!
                        async with node.stream(agent_run.ctx) as stream:
                            async for event in stream:
                                if isinstance(event, PartStartEvent):
                                    # Start of a new part - check if it has content
                                    # Check if this is a TextPart with initial content
                                    if isinstance(event.part, TextPart) and event.part.content:
                                        full_response_parts.append(event.part.content)
                                        yield f"data: {json.dumps({'type': 'text_delta', 'content': event.part.content})}\n\n"
                                    continue
                                elif isinstance(event, PartDeltaEvent):
                                    if isinstance(event.delta, TextPartDelta):
                                        # Stream text delta
                                        content = event.delta.content_delta
                                        full_response_parts.append(content)
                                        yield f"data: {json.dumps({'type': 'text_delta', 'content': content})}\n\n"
                                    elif isinstance(event.delta, ToolCallPartDelta):
                                        # Tool call is being constructed - we'll handle it in CallToolsNode
                                        pass
                                        
                    elif Agent.is_call_tools_node(node):
                        # The model wants to call tools
                        async with node.stream(agent_run.ctx) as stream:
                            current_tool_calls = {}
                            
                            async for event in stream:
                                if isinstance(event, FunctionToolCallEvent):
                                    # Tool is being called
                                    # Handle case where args might be a JSON string
                                    args = event.part.args
                                    if isinstance(args, str):
                                        try:
                                            args = json.loads(args)
                                        except json.JSONDecodeError:
                                            pass
                                    
                                    tool_data = {
                                        'tool_name': event.part.tool_name,
                                        'args': args,
                                        'tool_call_id': event.part.tool_call_id
                                    }
                                    current_tool_calls[event.part.tool_call_id] = tool_data
                                    yield f"data: {json.dumps({'type': 'tool_call', **tool_data})}\n\n"
                                    
                                elif isinstance(event, FunctionToolResultEvent):
                                    # Tool returned a result
                                    yield f"data: {json.dumps({'type': 'tool_return', 'tool_call_id': event.tool_call_id, 'content': str(event.result.content)})}\n\n"
                    
                    elif Agent.is_end_node(node):
                        # We've reached the end
                        break
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Get the final output for conversation history
            # In streaming mode, we need to use the parts we collected
            if full_response_parts:
                full_response = ''.join(full_response_parts)
            else:
                # Fallback to result.output if available
                full_response = agent_run.result.output if hasattr(agent_run, 'result') and agent_run.result else ''
            
            # Add assistant response to conversation
            conversation.append({
                "role": "assistant",
                "content": full_response
            })
            
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            yield f"data: {json.dumps({'type': 'error', 'error': error_detail})}\n\n"
    
    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )


@app.get(f"{settings.api_v1_prefix}/model", response_model=ModelInfo)
async def get_model():
    """Get the current model."""
    return ModelInfo(model=agent_manager.get_model())


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
        model=agent_manager.get_model()
    )


@app.delete(f"{settings.api_v1_prefix}/conversation")
async def clear_conversation():
    """Clear the conversation context."""
    global conversation
    conversation = []
    
    return {"status": "conversation cleared", "model": agent_manager.get_model()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)