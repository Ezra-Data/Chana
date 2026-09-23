from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[int] = None  # null = start new session


class ChatBotResponse(BaseModel):
    message: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    session_id: int
    metadata: Optional[Dict[str, Any]] = None  # nav deep-link, ticket ID, etc.
    is_fallback: bool = False  # true if LLM was unavailable


class ChatSessionResponse(BaseModel):
    id: int
    student_id: int
    resolved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    preview: Optional[str] = None

    class Config:
        from_attributes = True


class ChatMessageHistory(BaseModel):
    id: int
    role: str
    content: str
    intent: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True
