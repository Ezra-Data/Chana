from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import CreateAgentRequest, AgentResponse, StudentResponse
from app.middleware.auth import hash_password, require_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post(
    "/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_agent(data: CreateAgentRequest, db: AsyncSession = Depends(get_db)):
    """Admin creates a support agent account. Agent can only sign in, not register."""
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    agent = User(
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
        role=UserRole.AGENT,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)

    return AgentResponse.model_validate(agent)


from app.models.ticket import Ticket, TicketStatus
from sqlalchemy import select, func


@router.get(
    "/agents",
    response_model=list[AgentResponse],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all agent accounts with their real-time ticket workload."""
    result = await db.execute(
        select(User).where(User.role == UserRole.AGENT).order_by(User.created_at.desc())
    )
    agents = result.scalars().all()

    response = []
    for a in agents:
        load_res = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_agent_id == a.id,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
            )
        )
        active_count = load_res.scalar() or 0
        rating_res = await db.execute(
            select(func.avg(Ticket.rating), func.count(Ticket.rating)).where(
                Ticket.assigned_agent_id == a.id,
                Ticket.rating.isnot(None),
            )
        )
        avg_rating, count_ratings = rating_res.one()
        resp = AgentResponse.model_validate(a)
        resp.active_tickets_count = active_count
        resp.average_rating = round(float(avg_rating), 1) if avg_rating is not None else None
        resp.ratings_count = count_ratings or 0
        response.append(resp)

    return response


@router.patch(
    "/agents/{agent_id}/deactivate",
    response_model=AgentResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def deactivate_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Deactivate an agent account."""
    result = await db.execute(
        select(User).where(User.id == agent_id, User.role == UserRole.AGENT)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_active = False
    await db.flush()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.patch(
    "/agents/{agent_id}/activate",
    response_model=AgentResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def activate_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Re-activate an agent account."""
    result = await db.execute(
        select(User).where(User.id == agent_id, User.role == UserRole.AGENT)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_active = True
    await db.flush()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.delete(
    "/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Permanently delete an agent account. Unassigns their open tickets first."""
    result = await db.execute(
        select(User).where(User.id == agent_id, User.role == UserRole.AGENT)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Unassign open tickets so they go back to the queue
    open_tickets_res = await db.execute(
        select(Ticket).where(
            Ticket.assigned_agent_id == agent_id,
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
        )
    )
    for t in open_tickets_res.scalars().all():
        t.assigned_agent_id = None
        t.status = TicketStatus.OPEN

    await db.delete(agent)
    await db.flush()


@router.get(
    "/students",
    response_model=list[StudentResponse],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_students(db: AsyncSession = Depends(get_db)):
    """List all student accounts with their ticket counts."""
    result = await db.execute(
        select(User).where(User.role == UserRole.STUDENT).order_by(User.created_at.desc())
    )
    students = result.scalars().all()

    response = []
    for s in students:
        count_res = await db.execute(
            select(func.count(Ticket.id)).where(Ticket.student_id == s.id)
        )
        ticket_count = count_res.scalar() or 0
        resp = StudentResponse.model_validate(s)
        resp.ticket_count = ticket_count
        response.append(resp)

    return response
