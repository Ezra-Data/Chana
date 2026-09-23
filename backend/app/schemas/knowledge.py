from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class KnowledgeEntryCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source_doc: Optional[str] = None


class KnowledgeEntryUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None


class KnowledgeEntryResponse(BaseModel):
    id: int
    category: str
    title: str
    content: str
    source_doc: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
