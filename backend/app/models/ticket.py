import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(str, enum.Enum):
    GENERAL = "general"
    FEE_DISPUTE = "fee_dispute"
    MISSING_MARKS = "missing_marks"
    HARASSMENT = "harassment"
    CORRUPTION = "corruption"
    ASSAULT = "assault"
    ACADEMIC = "academic"
    FACILITY = "facility"
    FEEDBACK = "feedback"
    OTHER = "other"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracking_id = Column(String(20), unique=True, index=True, nullable=False)  # e.g., TKT-0042
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(SAEnum(TicketCategory), default=TicketCategory.GENERAL, nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(SAEnum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    queue_position = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    rating = Column(Integer, nullable=True)  # 1 to 5 stars
    rating_comment = Column(Text, nullable=True)
    rated_at = Column(DateTime, nullable=True)

    # Relationships
    student = relationship("User", foreign_keys=[student_id], lazy="selectin")
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id], lazy="selectin")
    messages = relationship("TicketMessage", back_populates="ticket", lazy="selectin",
                            order_by="TicketMessage.timestamp")

    def __repr__(self):
        return f"<Ticket {self.tracking_id} status={self.status}>"


class SenderType(str, enum.Enum):
    STUDENT = "student"
    AGENT = "agent"
    SYSTEM = "system"


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null for system messages
    sender_type = Column(SAEnum(SenderType), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    sender = relationship("User", lazy="selectin")

    def __repr__(self):
        return f"<TicketMessage ticket={self.ticket_id} sender_type={self.sender_type}>"
