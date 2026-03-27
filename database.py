"""
Database models and setup for call logging.
Uses SQLite for simplicity — swap to PostgreSQL for production.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./calls.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CallLog(Base):
    """Main call record — one per call."""
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, unique=True, index=True)
    direction = Column(String)  # inbound / outbound
    from_number = Column(String)
    to_number = Column(String)
    workflow = Column(String)
    status = Column(String)
    duration = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    context = Column(Text, nullable=True)  # JSON blob for workflow context


class CallTranscript(Base):
    """Individual transcript entries for a call."""
    __tablename__ = "call_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, index=True)
    role = Column(String)  # user / assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
