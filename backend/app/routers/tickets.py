from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketMessage, TicketStatus, SenderType
from datetime import datetime, timezone
from app.schemas.ticket import (
    CreateTicketRequest, TicketResponse, TicketListResponse,
    TicketMessageCreate, TicketMessageResponse, UpdateTicketStatus,
    RateTicketRequest,
)
from app.middleware.auth import get_current_user, require_role
from app.services import ticket_service
from app.services.ws_manager import manager as ws_manager

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


def _build_ticket_response(ticket: Ticket) -> TicketResponse:
    """Convert a Ticket ORM object to a response schema."""
    messages = []
    for msg in (ticket.messages or []):
        messages.append(TicketMessageResponse(
            id=msg.id,
            ticket_id=msg.ticket_id,
            sender_id=msg.sender_id,
            sender_type=msg.sender_type.value,
            sender_name=msg.sender.name if msg.sender else "System",
            message=msg.message,
            timestamp=msg.timestamp,
        ))

    return TicketResponse(
        id=ticket.id,
        tracking_id=ticket.tracking_id,
        student_id=ticket.student_id,
        student_name=ticket.student.name if ticket.student else None,
        student_reg_no=ticket.student.student_reg_no if ticket.student else None,
        category=ticket.category.value,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        assigned_agent_id=ticket.assigned_agent_id,
        assigned_agent_name=ticket.assigned_agent.name if ticket.assigned_agent else None,
        queue_position=ticket.queue_position,
        rating=ticket.rating,
        rating_comment=ticket.rating_comment,
        rated_at=ticket.rated_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        first_response_at=ticket.first_response_at,
        resolved_at=ticket.resolved_at,
        messages=messages,
    )


def _build_ticket_list_item(ticket: Ticket) -> TicketListResponse:
    return TicketListResponse(
        id=ticket.id,
        tracking_id=ticket.tracking_id,
        category=ticket.category.value,
        subject=ticket.subject,
        status=ticket.status.value,
        priority=ticket.priority.value,
        student_name=ticket.student.name if ticket.student else None,
        student_reg_no=ticket.student.student_reg_no if ticket.student else None,
        assigned_agent_name=ticket.assigned_agent.name if ticket.assigned_agent else None,
        queue_position=ticket.queue_position,
        rating=ticket.rating,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: CreateTicketRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new ticket (student)."""
    ticket = await ticket_service.create_ticket(
        db=db,
        student_id=current_user.id,
        subject=data.subject,
        description=data.description,
        category=data.category,
    )

    # Notify agents via WebSocket
    await ws_manager.broadcast_to_role("agent", "ticket:new", {
        "ticket_id": ticket.id,
        "tracking_id": ticket.tracking_id,
        "subject": ticket.subject,
        "priority": ticket.priority.value,
        "category": ticket.category.value,
    })

    return _build_ticket_response(ticket)


@router.get("", response_model=list[TicketListResponse])
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List tickets:
    - Student sees own tickets
    - Agent sees unassigned + their assigned tickets
    - Admin sees all tickets
    """
    query = select(Ticket)

    if current_user.role == UserRole.STUDENT:
        query = query.where(Ticket.student_id == current_user.id)
    elif current_user.role == UserRole.AGENT:
        query = query.where(
            or_(
                Ticket.assigned_agent_id == current_user.id,
                Ticket.assigned_agent_id.is_(None),
            )
        )
    # Admin sees all — no filter

    if status_filter:
        try:
            query = query.where(Ticket.status == TicketStatus(status_filter))
        except ValueError:
            pass

    if priority_filter:
        query = query.where(Ticket.priority == priority_filter)

    query = query.order_by(Ticket.created_at.desc())
    result = await db.execute(query)
    tickets = result.scalars().all()

    return [_build_ticket_list_item(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get ticket detail with full message timeline."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Access control
    if current_user.role == UserRole.STUDENT and ticket.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _build_ticket_response(ticket)


@router.post("/{ticket_id}/messages", response_model=TicketMessageResponse)
async def add_ticket_message(
    ticket_id: int,
    data: TicketMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a reply to a ticket (student or agent)."""
    # Determine sender type
    if current_user.role == UserRole.STUDENT:
        sender_type = "student"
    else:
        sender_type = "agent"

    msg = await ticket_service.add_message(
        db=db,
        ticket_id=ticket_id,
        sender_id=current_user.id,
        sender_type=sender_type,
        message=data.message,
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get the ticket for WebSocket notifications
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if ticket:
        event_data = {
            "ticket_id": ticket.id,
            "tracking_id": ticket.tracking_id,
            "message": data.message,
            "sender_name": current_user.name,
            "sender_type": sender_type,
        }
        # Notify the other party
        if sender_type == "agent":
            await ws_manager.send_to_user(ticket.student_id, "ticket:message", event_data)
        else:
            if ticket.assigned_agent_id:
                await ws_manager.send_to_user(ticket.assigned_agent_id, "ticket:message", event_data)
            await ws_manager.broadcast_to_role("agent", "ticket:message", event_data)

    return TicketMessageResponse(
        id=msg.id,
        ticket_id=msg.ticket_id,
        sender_id=msg.sender_id,
        sender_type=msg.sender_type.value,
        sender_name=current_user.name,
        message=msg.message,
        timestamp=msg.timestamp,
    )


@router.patch("/{ticket_id}/claim", response_model=TicketResponse)
async def claim_ticket(
    ticket_id: int,
    current_user: User = Depends(require_role(UserRole.AGENT, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Agent claims an unassigned ticket."""
    ticket = await ticket_service.claim_ticket(db, ticket_id, current_user.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Notify student
    await ws_manager.send_to_user(ticket.student_id, "ticket:update", {
        "ticket_id": ticket.id,
        "tracking_id": ticket.tracking_id,
        "status": ticket.status.value,
        "agent_name": current_user.name,
    })

    return _build_ticket_response(ticket)


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: int,
    data: UpdateTicketStatus,
    current_user: User = Depends(require_role(UserRole.AGENT, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update ticket status (agent/admin)."""
    ticket = await ticket_service.update_status(db, ticket_id, data.status, current_user.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found or invalid status")

    # Notify student
    await ws_manager.send_to_user(ticket.student_id, "ticket:update", {
        "ticket_id": ticket.id,
        "tracking_id": ticket.tracking_id,
        "status": ticket.status.value,
    })

    # Notify all agents
    await ws_manager.broadcast_to_role("agent", "ticket:update", {
        "ticket_id": ticket.id,
        "tracking_id": ticket.tracking_id,
        "status": ticket.status.value,
    })

    return _build_ticket_response(ticket)


@router.post("/{ticket_id}/rate", response_model=TicketResponse)
async def rate_ticket(
    ticket_id: int,
    data: RateTicketRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student rates human agent assistance after ticket is resolved."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role == UserRole.STUDENT and ticket.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if ticket.status != TicketStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Only resolved tickets can be rated")

    ticket.rating = data.rating
    ticket.rating_comment = data.comment
    ticket.rated_at = datetime.now(timezone.utc)

    # Add system message to timeline
    system_msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type=SenderType.SYSTEM,
        message=f"Student rated support assistance {data.rating}/5 stars." + (f' Feedback: "{data.comment}"' if data.comment else ""),
    )
    db.add(system_msg)
    await db.flush()
    await db.refresh(ticket)

    # Notify agent and admin of new rating
    event_data = {
        "ticket_id": ticket.id,
        "tracking_id": ticket.tracking_id,
        "rating": ticket.rating,
        "comment": ticket.rating_comment,
        "agent_id": ticket.assigned_agent_id,
    }
    if ticket.assigned_agent_id:
        await ws_manager.send_to_user(ticket.assigned_agent_id, "ticket:rated", event_data)
    await ws_manager.broadcast_to_role("admin", "ticket:rated", event_data)

    return _build_ticket_response(ticket)

