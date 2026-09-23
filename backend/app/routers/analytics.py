"""
Analytics router — provides dashboard data computed from real DB.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketStatus, TicketCategory
from app.models.knowledge import KnowledgeEntry
from app.models.chat import ChatSession, ChatMessage
from app.models.navigation import NavNode
from app.middleware.auth import require_role
from app.services import rag_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get analytics dashboard data computed from real DB."""

    # Total counts
    total_students = (await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.STUDENT)
    )).scalar() or 0

    total_agents = (await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.AGENT)
    )).scalar() or 0

    total_tickets = (await db.execute(
        select(func.count(Ticket.id))
    )).scalar() or 0

    open_tickets = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
    )).scalar() or 0

    in_progress_tickets = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.IN_PROGRESS)
    )).scalar() or 0

    resolved_tickets = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.RESOLVED)
    )).scalar() or 0

    total_kb_entries = (await db.execute(
        select(func.count(KnowledgeEntry.id))
    )).scalar() or 0

    total_chat_sessions = (await db.execute(
        select(func.count(ChatSession.id))
    )).scalar() or 0

    total_chat_messages = (await db.execute(
        select(func.count(ChatMessage.id))
    )).scalar() or 0

    # Tickets by category
    tickets_by_category = []
    for cat in TicketCategory:
        count = (await db.execute(
            select(func.count(Ticket.id)).where(Ticket.category == cat)
        )).scalar() or 0
        if count > 0:
            tickets_by_category.append({
                "category": cat.value.replace("_", " ").title(),
                "count": count,
            })

    # Tickets by status
    tickets_by_status = [
        {"status": "Open", "count": open_tickets},
        {"status": "In Progress", "count": in_progress_tickets},
        {"status": "Resolved", "count": resolved_tickets},
    ]

    # Top queried intents from chat messages
    intent_counts_result = await db.execute(
        select(ChatMessage.intent, func.count(ChatMessage.id))
        .where(ChatMessage.intent.isnot(None), ChatMessage.role == "assistant")
        .group_by(ChatMessage.intent)
        .order_by(func.count(ChatMessage.id).desc())
        .limit(10)
    )
    top_intents = [
        {"intent": row[0], "count": row[1]}
        for row in intent_counts_result.all()
    ]

    # Overall rating
    avg_rating_val = (await db.execute(
        select(func.avg(Ticket.rating)).where(Ticket.rating.isnot(None))
    )).scalar()
    avg_rating = round(float(avg_rating_val), 1) if avg_rating_val is not None else None

    # ChromaDB stats
    vector_stats = rag_service.get_collection_stats()

    return {
        "overview": {
            "total_students": total_students,
            "total_agents": total_agents,
            "total_tickets": total_tickets,
            "total_kb_entries": total_kb_entries,
            "total_chat_sessions": total_chat_sessions,
            "total_chat_messages": total_chat_messages,
            "vector_chunks": vector_stats["total_chunks"],
            "average_rating": avg_rating,
        },
        "tickets_by_status": tickets_by_status,
        "tickets_by_category": tickets_by_category,
        "top_intents": top_intents,
    }
