from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Sender(enum.Enum):
    PLAYER = "player"
    VALEZAP = "valezap"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    player_id = Column(String(128), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True))

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_token = Column(
        String(64),
        ForeignKey("chat_sessions.session_token", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender = Column(Enum(Sender), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("ChatSession", back_populates="messages")


__all__ = ["Base", "ChatSession", "Message", "Sender"]

