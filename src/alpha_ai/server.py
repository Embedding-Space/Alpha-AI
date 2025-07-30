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
from pydantic_ai.messages import (
    ModelResponse, ModelRequest, ToolCallPart, ToolReturnPart,
    TextPart, TextPartDelta, ToolCallPartDelta,
    PartStartEvent, PartDeltaEvent, FinalResultEvent,
    FunctionToolCallEvent, FunctionToolResultEvent
)
from alpha_ai.settings import settings
from alpha_ai.agent import agent_manager
from alpha_ai.database import init_db, get_db, conversation_manager, EventType
from pydantic_ai import Agent


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
    
    # Initialize database
    init_db()
    print("Database initialized successfully")
    
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
        "mcp_servers": list(agent_manager.mcp_servers.keys()),
        "streaming": settings.streaming
    }


@app.post(f"{settings.api_v1_prefix}/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and get a response."""
    # Add user message event
    conversation_manager.add_user_message(db, request.message)
    
    # Generate AI response and get full result
    # TODO: Pass conversation history from database
    result = await agent_manager.chat_with_result(request.message, [])
    response_text = result.output
    
    # Process messages to extract events
    tool_calls = []
    messages = result.new_messages()
    
    # Store each part as an event
    for msg in messages:
        if isinstance(msg, ModelResponse):
            # Process each part of the model response
            current_text_parts = []
            
            for part in msg.parts:
                if isinstance(part, TextPart):
                    # Accumulate text parts
                    current_text_parts.append(part.content)
                elif isinstance(part, ToolCallPart):
                    # Save any accumulated text first
                    if current_text_parts:
                        conversation_manager.add_assistant_message(db, ''.join(current_text_parts))
                        current_text_parts = []
                    
                    # Save tool call event
                    args = part.args if isinstance(part.args, dict) else {}
                    conversation_manager.add_tool_call(db, part.tool_name, args, part.tool_call_id)
                    
                    # Track for response
                    tool_call = ToolCall(
                        tool_name=part.tool_name,
                        args=args,
                        tool_call_id=part.tool_call_id
                    )
                    tool_calls.append([tool_call, None])
            
            # Save any remaining text
            if current_text_parts:
                conversation_manager.add_assistant_message(db, ''.join(current_text_parts))
                
        elif isinstance(msg, ModelRequest):
            # Process tool returns
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    # Save tool response event
                    conversation_manager.add_tool_response(
                        db, 
                        part.tool_name, 
                        str(part.content), 
                        part.tool_call_id
                    )
                    
                    # Update tool_calls list
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
        model=agent_manager.get_model(),
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
    # Add user message to database
    conversation_manager.add_user_message(db, request.message)
    
    async def generate():
        import json
        try:
            # Initialize agent if needed
            await agent_manager.initialize()
            
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'model': agent_manager.get_model()})}\n\n"
            
            # Track current assistant text being accumulated
            current_text_parts = []
            
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
                        # First, save any accumulated text
                        if current_text_parts:
                            conversation_manager.add_assistant_message(db, ''.join(current_text_parts))
                            current_text_parts = []
                        
                        async with node.stream(agent_run.ctx) as stream:
                            tool_name_map = {}  # Map tool_call_id to tool_name for responses
                            
                            async for event in stream:
                                if isinstance(event, FunctionToolCallEvent):
                                    # Tool is being called
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
                                    
                                    # Save tool call event to database
                                    conversation_manager.add_tool_call(
                                        db, 
                                        event.part.tool_name, 
                                        args, 
                                        event.part.tool_call_id
                                    )
                                    
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
                                    
                                    # Save tool response event to database
                                    conversation_manager.add_tool_response(
                                        db,
                                        tool_name,
                                        str(event.result.content),
                                        event.tool_call_id
                                    )
                                    
                                    # Stream tool response to client
                                    yield f"data: {json.dumps({'type': 'tool_return', 'tool_call_id': event.tool_call_id, 'content': str(event.result.content)})}\n\n"
                    
                    elif Agent.is_end_node(node):
                        # We've reached the end
                        break
            
            # Save any remaining assistant text
            if current_text_parts:
                conversation_manager.add_assistant_message(db, ''.join(current_text_parts))
            
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
    return ModelInfo(model=agent_manager.get_model())


@app.get(f"{settings.api_v1_prefix}/models", response_model=ModelsResponse)
async def get_models():
    """Get all available models."""
    return ModelsResponse(
        models=list(agent_manager.get_available_models().values()),
        current=agent_manager.get_model()
    )


@app.post(f"{settings.api_v1_prefix}/conversation/new")
async def new_conversation(request: Dict[str, str], db: Session = Depends(get_db)):
    """Start a new conversation with a specific model."""
    model = request.get("model")
    if not model:
        raise HTTPException(status_code=400, detail="Model is required")
    
    # Clear the current conversation
    conversation_manager.clear_conversation(db)
    
    # Set the new model
    try:
        await agent_manager.set_model(model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"status": "new conversation started", "model": model}


@app.get(f"{settings.api_v1_prefix}/conversation", response_model=ConversationResponse)
async def get_conversation(limit: int = 50, db: Session = Depends(get_db)):
    """Get the conversation history by reconstructing from events."""
    conversation = conversation_manager.get_current_conversation(db)
    
    if not conversation:
        return ConversationResponse(
            messages=[],
            total_messages=0,
            model=agent_manager.get_model()
        )
    
    # Reconstruct messages from events
    messages = []
    current_tool_calls = []  # Accumulate tool calls for assistant messages
    pending_tool_map = {}  # Map tool_call_id to ToolCall
    
    # Get the last N events (increase limit to account for tool events)
    events = conversation.events[-limit*3:]  # Rough estimate: each message might have tool calls
    
    for event in events:
        if event.event_type == EventType.USER:
            # User message - simple
            message = MessageWithToolCalls(
                role="user",
                content=event.content,
                timestamp=event.created_at,
                tool_calls=None
            )
            messages.append(message)
            
        elif event.event_type == EventType.ASSISTANT:
            # Assistant message - check if we have accumulated tool calls
            message = MessageWithToolCalls(
                role="assistant",
                content=event.content,
                timestamp=event.created_at,
                tool_calls=current_tool_calls if current_tool_calls else None
            )
            messages.append(message)
            # Reset tool calls for next message
            current_tool_calls = []
            pending_tool_map = {}
            
        elif event.event_type == EventType.TOOL_CALL:
            # Tool call - create ToolCall object
            data = event.data or {}
            tool_call = ToolCall(
                tool_name=data.get("tool_name", "unknown"),
                args=data.get("args", {}),
                tool_call_id=data.get("tool_call_id", "")
            )
            pending_tool_map[tool_call.tool_call_id] = (tool_call, None)
            
        elif event.event_type == EventType.TOOL_RESPONSE:
            # Tool response - pair with its call
            data = event.data or {}
            tool_call_id = data.get("tool_call_id", "")
            
            if tool_call_id in pending_tool_map:
                tool_call, _ = pending_tool_map[tool_call_id]
                tool_return = ToolReturn(
                    tool_name=data.get("tool_name", "unknown"),
                    content=event.content,
                    tool_call_id=tool_call_id
                )
                # Update the pair and add to current_tool_calls
                current_tool_calls.append((tool_call, tool_return))
                del pending_tool_map[tool_call_id]
        
        elif event.event_type == EventType.SYSTEM:
            # System message
            message = MessageWithToolCalls(
                role="system",
                content=event.content,
                timestamp=event.created_at,
                tool_calls=None
            )
            messages.append(message)
    
    # Only return the last 'limit' actual messages
    messages = messages[-limit:]
    
    return ConversationResponse(
        messages=messages,
        total_messages=len(conversation.events),
        model=agent_manager.get_model()
    )


@app.delete(f"{settings.api_v1_prefix}/conversation")
async def clear_conversation(db: Session = Depends(get_db)):
    """Clear the conversation context."""
    conversation_manager.clear_conversation(db)
    
    return {"status": "conversation cleared", "model": agent_manager.get_model()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)