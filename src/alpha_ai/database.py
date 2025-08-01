"""Conversation-centric database models for Alpha AI."""

from datetime import datetime, timezone
from typing import Optional, Generator
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from .settings import settings

Base = declarative_base()


class Conversation(Base):
    """A conversation with complete message history."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    model = Column(String, nullable=False)
    system_prompt_filename = Column(String, nullable=True)
    messages_json = Column(Text, nullable=False, default="[]")  # PydanticAI ModelMessage list as JSON
    version = Column(Integer, default=1, nullable=False)  # For optimistic locking
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ConversationEvent(Base):
    """Lightweight events for future multi-UI support."""
    __tablename__ = "conversation_events"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)  # 'message_added', 'model_changed', etc
    event_data = Column(Text, nullable=False)  # JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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