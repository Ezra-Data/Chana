"""
Ticket Service — lifecycle management, priority assignment, queue positioning.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket, TicketMessage, TicketStatus, TicketPriority, TicketCategory, SenderType
from app.models.user import User, UserRole


async def generate_tracking_id(db: AsyncSession) -> str:
    """Generate next sequential tracking ID."""
    result = await db.execute(select(func.count(Ticket.id)))
    count = result.scalar() or 0
    return f"TKT-{count + 1:04d}"


async def find_least_loaded_agent(db: AsyncSession) -> Tuple[Optional[int], Optional[str], int]:
    """
    Agent Load Balancing:
    Finds the active agent with the least number of active tickets (OPEN or IN_PROGRESS).
    Returns (assigned_agent_id, assigned_agent_name, queue_position).
    """
    agents_res = await db.execute(
        select(User).where(User.role == UserRole.AGENT, User.is_active == True)
    )
    active_agents = agents_res.scalars().all()

    if not active_agents:
        res = await db.execute(
            select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
        )
        queue_pos = (res.scalar() or 0) + 1
        return None, None, queue_pos

    least_agent = None
    min_load = float('inf')

    for agent in active_agents:
        load_res = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_agent_id == agent.id,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
            )
        )
        current_load = load_res.scalar() or 0
        if current_load < min_load:
            min_load = current_load
            least_agent = agent

    queue_pos = min_load + 1
    return least_agent.id, least_agent.name, queue_pos


async def create_ticket(
    db: AsyncSession,
    student_id: int,
    subject: str,
    description: str,
    category: str = "general",
) -> Ticket:
    """Create a new ticket with automatic agent load balancing and queue positioning."""
    tracking_id = await generate_tracking_id(db)

    # Map category string to enum
    try:
        cat_enum = TicketCategory(category)
    except ValueError:
        cat_enum = TicketCategory.GENERAL

    # Auto-assign priority
    critical_cats = {TicketCategory.HARASSMENT, TicketCategory.CORRUPTION, TicketCategory.ASSAULT}
    high_cats = {TicketCategory.FEE_DISPUTE, TicketCategory.MISSING_MARKS}

    if cat_enum in critical_cats:
        priority = TicketPriority.CRITICAL
    elif cat_enum in high_cats:
        priority = TicketPriority.HIGH
    elif cat_enum == TicketCategory.FEEDBACK:
        priority = TicketPriority.LOW
    else:
        priority = TicketPriority.MEDIUM

    # Agent load balancing & queue position
    assigned_agent_id, assigned_agent_name, queue_pos = await find_least_loaded_agent(db)

    ticket = Ticket(
        tracking_id=tracking_id,
        student_id=student_id,
        category=cat_enum,
        subject=subject,
        description=description,
        status=TicketStatus.OPEN,
        priority=priority,
        assigned_agent_id=assigned_agent_id,
        queue_position=queue_pos,
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def claim_ticket(db: AsyncSession, ticket_id: int, agent_id: int) -> Optional[Ticket]:
    """Agent claims a ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None

    ticket.assigned_agent_id = agent_id
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.updated_at = datetime.now(timezone.utc)

    # Add system message
    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type=SenderType.SYSTEM,
        message="Ticket has been claimed by a support agent.",
    )
    db.add(msg)
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def update_status(
    db: AsyncSession, ticket_id: int, new_status: str, agent_id: Optional[int] = None
) -> Optional[Ticket]:
    """Update ticket status."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None

    try:
        status_enum = TicketStatus(new_status)
    except ValueError:
        return None

    ticket.status = status_enum
    ticket.updated_at = datetime.now(timezone.utc)
    if status_enum == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    if status_enum == TicketStatus.RESOLVED and ticket.assigned_agent_id:
        # Advance queue position for remaining tickets assigned to this agent
        await db.execute(
            update(Ticket)
            .where(
                Ticket.assigned_agent_id == ticket.assigned_agent_id,
                Ticket.id != ticket.id,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
                Ticket.queue_position > 1,
            )
            .values(queue_position=Ticket.queue_position - 1)
        )
        await db.flush()

    # Add system message
    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type=SenderType.SYSTEM,
        message=f"Ticket status changed to {status_enum.value.replace('_', ' ').title()}.",
    )
    db.add(msg)
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def add_message(
    db: AsyncSession,
    ticket_id: int,
    sender_id: int,
    sender_type: str,
    message: str,
) -> Optional[TicketMessage]:
    """Add a message to a ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None

    try:
        st = SenderType(sender_type)
    except ValueError:
        st = SenderType.STUDENT

    msg = TicketMessage(
        ticket_id=ticket_id,
        sender_id=sender_id,
        sender_type=st,
        message=message,
    )
    db.add(msg)

    # Update ticket timestamp
    ticket.updated_at = datetime.now(timezone.utc)

    # Track first response time for agents
    if st == SenderType.AGENT and not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(msg)
    return msg
