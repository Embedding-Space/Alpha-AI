"""FastAPI server for Alpha AI."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from alpha_ai.models import (
    ChatRequest, ChatResponse, ModelInfo, 
    ConversationResponse, ChatMessage, MessageWithToolCalls,
    ToolCall, ToolReturn, ModelsResponse
)
from typing import List
from pydantic_ai.messages import (
    ModelResponse, ModelRequest, ToolCallPart, ToolReturnPart,
    TextPart, TextPartDelta, ToolCallPartDelta,
    PartStartEvent, PartDeltaEvent, FinalResultEvent,
    FunctionToolCallEvent, FunctionToolResultEvent,
    SystemPromptPart, UserPromptPart
)
from alpha_ai.settings import settings
from alpha_ai.database import init_db, get_db
from alpha_ai.conversation import conversation_manager, event_bus
from alpha_ai.model_discovery import model_discovery
from pydantic_ai import Agent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting Alpha AI server...")
    if settings.mcp_config_file:
        print(f"MCP config file: {settings.mcp_config_file}")
        if settings.mcp_servers:
            print(f"Enabled MCP servers: {', '.join(settings.mcp_servers)}")
    
    # Initialize database
    init_db()
    print("Database initialized successfully")
    
    # Load the most recent conversation
    from alpha_ai.database import get_db
    db_gen = get_db()
    db = next(db_gen)
    try:
        conv = await conversation_manager.load_most_recent(db)
        if conv:
            print(f"Loaded conversation {conv.id} with model {conv.model}")
        else:
            print("No existing conversations found")
    finally:
        db_gen.close()
    
    yield
    
    # Shutdown
    print("Shutting down Alpha AI server...")
    if conversation_manager.current_conversation:
        await conversation_manager.current_conversation.dispose_agent()


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

# Mount static files from frontend build
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

# Serve from frontend dist if it exists
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    serve_from = frontend_dist
else:
    serve_from = None


@app.get("/")
async def root():
    """Serve the web UI."""
    if serve_from:
        html_file = serve_from / "index.html"
        if html_file.exists():
            return FileResponse(html_file)
    return {"message": "Alpha AI API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    current_conv = conversation_manager.get_current()
    return {
        "status": "healthy",
        "model": current_conv.model if current_conv else None,
        "conversation_id": current_conv.id if current_conv else None,
        "streaming": settings.streaming
    }


@app.post(f"{settings.api_v1_prefix}/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and get a response."""
    # Get current conversation
    current_conv = conversation_manager.get_current()
    if not current_conv:
        raise HTTPException(status_code=400, detail="No active conversation. Please start a new conversation.")
    
    # Generate AI response using the conversation
    result = await current_conv.chat(request.message)
    response_text = str(result.output) if result.output else "I couldn't generate a response."
    
    # Save conversation state
    await conversation_manager.save_current(db)
    
    # Process messages to extract tool calls for the response
    tool_calls = []
    messages = result.new_messages()
    
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    # Handle args serialization
                    args = part.args
                    if isinstance(args, str):
                        try:
                            import json
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"value": args}
                    elif not isinstance(args, dict):
                        args = {"value": str(args)}
                    
                    tool_call = ToolCall(
                        tool_name=part.tool_name,
                        args=args,
                        tool_call_id=part.tool_call_id
                    )
                    tool_calls.append([tool_call, None])
                    
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    # Update tool_calls list with response
                    for tc_pair in tool_calls:
                        if tc_pair[0].tool_call_id == part.tool_call_id:
                            tool_return = ToolReturn(
                                tool_name=part.tool_name,
                                content=str(part.content),
                                tool_call_id=part.tool_call_id
                            )
                            tc_pair[1] = tool_return
    
    # Convert to tuples for response
    tool_calls_tuples = [(tc[0], tc[1]) for tc in tool_calls if tc[1] is not None]
    
    return ChatResponse(
        response=response_text,
        model=current_conv.model,
        usage={
            "request_tokens": len(request.message.split()),
            "response_tokens": len(response_text.split()),
            "total_tokens": len(request.message.split()) + len(response_text.split())
        },
        tool_calls=tool_calls_tuples if tool_calls_tuples else None
    )


@app.post(f"{settings.api_v1_prefix}/chat/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """Stream a response using Server-Sent Events with proper graph-based streaming."""
    # Get current conversation
    current_conv = conversation_manager.get_current()
    if not current_conv:
        raise HTTPException(status_code=400, detail="No active conversation. Please start a new conversation.")
    
    async def generate():
        import json
        try:
            # Ensure agent is ready
            await current_conv.ensure_agent()
            
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'model': current_conv.model})}\n\n"
            
            # Use agent.iter() to walk through the execution graph
            async with current_conv._agent.iter(request.message, message_history=current_conv.history) as agent_run:
                # Initialize current_text_parts at the beginning of streaming
                current_text_parts = []
                
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
                                        current_text_parts.append(event.part.content)
                                        yield f"data: {json.dumps({'type': 'text_delta', 'content': event.part.content})}\n\n"
                                    continue
                                elif isinstance(event, PartDeltaEvent):
                                    if isinstance(event.delta, TextPartDelta):
                                        # Stream text delta
                                        content = event.delta.content_delta
                                        current_text_parts.append(content)
                                        yield f"data: {json.dumps({'type': 'text_delta', 'content': content})}\n\n"
                                    elif isinstance(event.delta, ToolCallPartDelta):
                                        # Tool call is being constructed - we'll handle it in CallToolsNode
                                        pass
                                        
                    elif Agent.is_call_tools_node(node):
                        # The model wants to call tools
                        
                        async with node.stream(agent_run.ctx) as stream:
                            tool_name_map = {}  # Map tool_call_id to tool_name for responses
                            
                            async for event in stream:
                                if isinstance(event, FunctionToolCallEvent):
                                    # Tool is being called
                                    # Debug: log what we're getting
                                    print(f"DEBUG STREAMING: Tool call {event.part.tool_name} - event.part.args type: {type(event.part.args)}, value: {event.part.args}")
                                    
                                    # Handle case where args might be a JSON string
                                    args = event.part.args
                                    if isinstance(args, str):
                                        try:
                                            args = json.loads(args)
                                        except json.JSONDecodeError:
                                            # If it's not valid JSON, wrap it in a dict
                                            args = {"value": args}
                                    elif not isinstance(args, dict):
                                        # If it's not a dict or string, convert to dict
                                        args = {"value": str(args)}
                                    
                                    # Note: We'll save to database after streaming completes
                                    
                                    # Track tool name for response
                                    tool_name_map[event.part.tool_call_id] = event.part.tool_name
                                    
                                    # Stream tool call to client
                                    tool_data = {
                                        'tool_name': event.part.tool_name,
                                        'args': args,
                                        'tool_call_id': event.part.tool_call_id
                                    }
                                    yield f"data: {json.dumps({'type': 'tool_call', **tool_data})}\n\n"
                                    
                                elif isinstance(event, FunctionToolResultEvent):
                                    # Tool returned a result
                                    tool_name = tool_name_map.get(event.tool_call_id, "unknown")
                                    
                                    # Note: We'll save to database after streaming completes
                                    
                                    # Stream tool response to client
                                    yield f"data: {json.dumps({'type': 'tool_return', 'tool_call_id': event.tool_call_id, 'content': str(event.result.content)})}\n\n"
                    
                    elif Agent.is_end_node(node):
                        # We've reached the end
                        break
            
            # The conversation's history is already updated by the agent run
            # Get the result (it's a property, not async)
            result = agent_run.result
            current_conv.history.extend(result.new_messages())
            
            # Save conversation state
            await conversation_manager.save_current(db)
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
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
    current_conv = conversation_manager.get_current()
    return ModelInfo(model=current_conv.model if current_conv else None)


@app.get(f"{settings.api_v1_prefix}/models", response_model=ModelsResponse)
async def get_models():
    """Get all available models."""
    # Refresh model list on every request
    models = await model_discovery.discover_all()
    
    current_conv = conversation_manager.get_current()
    return ModelsResponse(
        models=models,
        current=current_conv.model if current_conv else None
    )


@app.get(f"{settings.api_v1_prefix}/prompts")
async def get_prompts():
    """Get all available system prompt files."""
    prompts_dir = Path("/app/system_prompts")
    prompts = ["none"]  # Always include "none" as the first option
    
    if prompts_dir.exists() and prompts_dir.is_dir():
        # Get all .md files in the directory
        for file in sorted(prompts_dir.glob("*.md")):
            prompts.append(file.name)  # Include full filename with .md extension
    
    return {"prompts": prompts}


@app.get(f"{settings.api_v1_prefix}/prompts/{{prompt_name}}")
async def get_prompt_content(prompt_name: str):
    """Get the content of a specific prompt file."""
    if prompt_name == "none":
        return {"content": ""}
    
    prompt_file = Path(f"/app/system_prompts/{prompt_name}")
    if not prompt_file.exists():
        raise HTTPException(status_code=404, detail="Prompt file not found")
    
    try:
        content = prompt_file.read_text(encoding="utf-8")
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading prompt file: {str(e)}")


@app.post(f"{settings.api_v1_prefix}/conversation/new")
async def new_conversation(request: Dict[str, str], db: Session = Depends(get_db)):
    """Start a new conversation with a specific model and prompt."""
    model = request.get("model")
    if not model:
        raise HTTPException(status_code=400, detail="Model is required")
    
    prompt_name = request.get("system_prompt", "")
    system_prompt = ""
    
    # Load the system prompt content if a filename is specified
    if prompt_name:  # If not empty string
        prompt_file = Path(f"/app/system_prompts/{prompt_name}")
        if prompt_file.exists():
            try:
                system_prompt = prompt_file.read_text(encoding="utf-8")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading prompt file: {str(e)}")
    
    # Create new conversation
    await conversation_manager.create_new_conversation(
        db=db,
        model=model,
        system_prompt_filename=prompt_name if prompt_name else None,
        system_prompt_content=system_prompt if system_prompt else None
    )
    
    return {"status": "new conversation started", "model": model, "prompt": prompt_name}


@app.get(f"{settings.api_v1_prefix}/conversation", response_model=ConversationResponse)
async def get_conversation(limit: int = 50, db: Session = Depends(get_db)):
    """Get the conversation history."""
    current_conv = conversation_manager.get_current()
    
    if not current_conv:
        return ConversationResponse(
            messages=[],
            total_messages=0,
            model=None,
            system_prompt=None
        )
    
    # Convert PydanticAI messages to our API format
    messages = []
    for msg in current_conv.history[-limit:]:
        if isinstance(msg, ModelRequest):
            # Process request parts
            for part in msg.parts:
                if isinstance(part, SystemPromptPart):
                    messages.append(MessageWithToolCalls(
                        role="system",
                        content=part.content,
                        timestamp=part.timestamp or datetime.now(timezone.utc),
                        tool_calls=None
                    ))
                elif isinstance(part, UserPromptPart):
                    messages.append(MessageWithToolCalls(
                        role="user",
                        content=part.content,
                        timestamp=part.timestamp or datetime.now(timezone.utc),
                        tool_calls=None
                    ))
        elif isinstance(msg, ModelResponse):
            # Collect text and tool calls
            text_parts = []
            tool_calls = []
            
            for part in msg.parts:
                if isinstance(part, TextPart):
                    text_parts.append(part.content)
                elif isinstance(part, ToolCallPart):
                    # Need to find matching tool response
                    tool_call = ToolCall(
                        tool_name=part.tool_name,
                        args=part.args if isinstance(part.args, dict) else {"value": str(part.args)},
                        tool_call_id=part.tool_call_id
                    )
                    # TODO: Match with tool responses
                    tool_calls.append((tool_call, None))
            
            if text_parts or tool_calls:
                messages.append(MessageWithToolCalls(
                    role="assistant",
                    content="".join(text_parts) if text_parts else "",
                    timestamp=msg.timestamp or datetime.now(timezone.utc),
                    tool_calls=tool_calls if tool_calls else None
                ))
    
    return ConversationResponse(
        messages=messages,
        total_messages=len(current_conv.history),
        model=current_conv.model,
        system_prompt=current_conv.system_prompt_filename
    )


@app.delete(f"{settings.api_v1_prefix}/conversation")
async def clear_conversation(db: Session = Depends(get_db)):
    """Clear the conversation context by resetting message history."""
    current_conv = conversation_manager.get_current()
    
    if current_conv:
        # Dispose the existing agent to clear any internal state
        if current_conv._agent:
            await current_conv.dispose_agent()
        
        # Clear the message history but keep the model and prompt
        current_conv.history = []
        
        # If there was a system prompt, restore it as the first message
        if current_conv.system_prompt_filename:
            prompt_file = Path(f"/app/system_prompts/{current_conv.system_prompt_filename}")
            if prompt_file.exists():
                try:
                    system_prompt_content = prompt_file.read_text(encoding="utf-8")
                    first_request = ModelRequest(parts=[
                        SystemPromptPart(content=system_prompt_content)
                    ])
                    current_conv.history.append(first_request)
                except Exception:
                    pass  # If we can't read the prompt, just leave history empty
        
        # Save the cleared conversation
        await conversation_manager.save_current(db)
        
        return {"status": "conversation cleared", "model": current_conv.model}
    
    return {"status": "no conversation to clear", "model": None}


# Catch-all route for SPA client-side routing - must be last!
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the SPA for any unmatched routes (client-side routing)."""
    if serve_from:
        html_file = serve_from / "index.html"
        if html_file.exists():
            return FileResponse(html_file)
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)