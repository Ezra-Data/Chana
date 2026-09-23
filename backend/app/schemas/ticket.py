from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Ticket Schemas ────────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    category: str = "general"
    subject: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)


class UpdateTicketStatus(BaseModel):
    status: str  # "open", "in_progress", "resolved"


class RateTicketRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class TicketMessageCreate(BaseModel):
    message: str = Field(..., min_length=1)


class TicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: Optional[int] = None
    sender_type: str
    sender_name: Optional[str] = None
    message: str
    timestamp: datetime

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    id: int
    tracking_id: str
    student_id: int
    student_name: Optional[str] = None
    student_reg_no: Optional[str] = None
    category: str
    subject: str
    description: str
    status: str
    priority: str
    assigned_agent_id: Optional[int] = None
    assigned_agent_name: Optional[str] = None
    queue_position: Optional[int] = None
    rating: Optional[int] = None
    rating_comment: Optional[str] = None
    rated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    messages: List[TicketMessageResponse] = []

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    id: int
    tracking_id: str
    category: str
    subject: str
    status: str
    priority: str
    student_name: Optional[str] = None
    student_reg_no: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    queue_position: Optional[int] = None
    rating: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
