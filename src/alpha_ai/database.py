"""Event-based database models and operations for Alpha AI."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, Generator
from enum import Enum
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.engine import Engine

from .settings import settings

Base = declarative_base()


class EventType(str, Enum):
    """Types of events in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"


class Conversation(Base):
    """A conversation session."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to events
    events = relationship("ConversationEvent", back_populates="conversation", order_by="ConversationEvent.position", cascade="all, delete-orphan")


class ConversationEvent(Base):
    """An event in a conversation (message, tool call, etc)."""
    __tablename__ = "conversation_events"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    position = Column(Integer, nullable=False)  # Order within conversation
    event_type = Column(SQLEnum(EventType), nullable=False)
    content = Column(Text, nullable=True)  # Text content for messages
    data = Column(JSON, nullable=True)  # Additional data (tool names, args, etc)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    conversation = relationship("Conversation", back_populates="events")


# Database initialization
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None


def init_db():
    """Initialize the database."""
    global engine, SessionLocal
    
    engine = create_engine(settings.database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get a database session."""
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ConversationManager:
    """Manages conversation persistence with event-based storage."""
    
    def __init__(self):
        self.current_conversation_id: Optional[int] = None
        self.event_position = 0
    
    def start_new_conversation(self, db: Session) -> int:
        """Start a new conversation."""
        conversation = Conversation()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        self.current_conversation_id = conversation.id
        self.event_position = 0
        return conversation.id
    
    def add_event(
        self, 
        db: Session, 
        event_type: EventType, 
        content: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> ConversationEvent:
        """Add an event to the current conversation."""
        if self.current_conversation_id is None:
            self.start_new_conversation(db)
        
        event = ConversationEvent(
            conversation_id=self.current_conversation_id,
            position=self.event_position,
            event_type=event_type,
            content=content,
            data=data
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        
        self.event_position += 1
        return event
    
    def add_user_message(self, db: Session, content: str) -> ConversationEvent:
        """Add a user message event."""
        return self.add_event(db, EventType.USER, content=content)
    
    def add_assistant_message(self, db: Session, content: str) -> ConversationEvent:
        """Add an assistant message event."""
        return self.add_event(db, EventType.ASSISTANT, content=content)
    
    def add_tool_call(self, db: Session, tool_name: str, args: Dict[str, Any], tool_call_id: str) -> ConversationEvent:
        """Add a tool call event."""
        return self.add_event(
            db, 
            EventType.TOOL_CALL,
            data={
                "tool_name": tool_name,
                "args": args,
                "tool_call_id": tool_call_id
            }
        )
    
    def add_tool_response(self, db: Session, tool_name: str, content: str, tool_call_id: str) -> ConversationEvent:
        """Add a tool response event."""
        return self.add_event(
            db,
            EventType.TOOL_RESPONSE,
            content=content,
            data={
                "tool_name": tool_name,
                "tool_call_id": tool_call_id
            }
        )
    
    def add_system_message(self, db: Session, content: str) -> ConversationEvent:
        """Add a system message event."""
        return self.add_event(db, EventType.SYSTEM, content=content)
    
    def get_current_conversation(self, db: Session) -> Optional[Conversation]:
        """Get the current conversation with all events."""
        if self.current_conversation_id is None:
            # Try to get the most recent conversation
            conversation = db.query(Conversation).order_by(Conversation.created_at.desc()).first()
            if conversation:
                self.current_conversation_id = conversation.id
                # Set position to the next available position
                last_event = db.query(ConversationEvent).filter_by(
                    conversation_id=conversation.id
                ).order_by(ConversationEvent.position.desc()).first()
                self.event_position = (last_event.position + 1) if last_event else 0
                return conversation
            return None
        
        return db.query(Conversation).filter_by(id=self.current_conversation_id).first()
    
    def clear_conversation(self, db: Session):
        """Clear the current conversation by starting a new one."""
        # Don't delete old conversations - just start fresh
        self.current_conversation_id = None
        self.event_position = 0
        
        # Start a new conversation
        self.start_new_conversation(db)


# Global conversation manager
conversation_manager = ConversationManager()