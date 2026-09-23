from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ─── Auth Schemas ───────────────────────────────────────────────

class StudentRegister(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    student_reg_no: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ─── User Schemas ───────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    student_reg_no: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateAgentRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class AgentResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    active_tickets_count: int = 0
    average_rating: Optional[float] = None
    ratings_count: int = 0

    class Config:
        from_attributes = True


class StudentResponse(BaseModel):
    id: int
    email: str
    name: str
    student_reg_no: Optional[str] = None
    is_active: bool
    created_at: datetime
    ticket_count: int = 0

    class Config:
        from_attributes = True


# Forward reference resolution
TokenResponse.model_rebuild()
