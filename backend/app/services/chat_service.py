"""
Chat Orchestrator Service — routes messages by intent.

Flow:
1. Receive message
2. Keyword safety net → force 'sensitive' if trigger terms detected
3. Call 1: classify_intent() → get intent + confidence
4. If confidence < 0.6 → ask clarifying question
5. Route by intent:
   - faq → RAG retrieval → Call 2: generate_answer()
   - sensitive → auto-create ticket → return tracking ID
   - ticket_status → query DB → return status
   - navigation → match NavNode → return deep-link
"""

import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket, TicketMessage, TicketStatus, TicketPriority, TicketCategory, SenderType
from app.models.navigation import NavNode
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.services import deepseek_service
from app.services import rag_service
from app.services.ticket_service import find_least_loaded_agent

logger = logging.getLogger(__name__)

# ─── Sensitive Keyword Safety Net ─────────────────────────────
# These terms FORCE ticket creation regardless of LLM classification

SENSITIVE_TRIGGER_TERMS = {
    "harassment": TicketCategory.HARASSMENT,
    "harassed": TicketCategory.HARASSMENT,
    "harassing": TicketCategory.HARASSMENT,
    "sexually": TicketCategory.HARASSMENT,
    "sexual harassment": TicketCategory.HARASSMENT,
    "assault": TicketCategory.ASSAULT,
    "assaulted": TicketCategory.ASSAULT,
    "attacked": TicketCategory.ASSAULT,
    "violence": TicketCategory.ASSAULT,
    "violent": TicketCategory.ASSAULT,
    "beaten": TicketCategory.ASSAULT,
    "corruption": TicketCategory.CORRUPTION,
    "corrupt": TicketCategory.CORRUPTION,
    "bribe": TicketCategory.CORRUPTION,
    "bribery": TicketCategory.CORRUPTION,
    "pay for marks": TicketCategory.CORRUPTION,
    "buy marks": TicketCategory.CORRUPTION,
    "pay him directly": TicketCategory.CORRUPTION,
    "pay her directly": TicketCategory.CORRUPTION,
    "pay directly": TicketCategory.CORRUPTION,
    "demanding cash": TicketCategory.CORRUPTION,
    "overcharged": TicketCategory.FEE_DISPUTE,
    "overcharge": TicketCategory.FEE_DISPUTE,
    "fee dispute": TicketCategory.FEE_DISPUTE,
    "wrong fee": TicketCategory.FEE_DISPUTE,
    "extra charges": TicketCategory.FEE_DISPUTE,
    "missing marks": TicketCategory.MISSING_MARKS,
    "missing mark": TicketCategory.MISSING_MARKS,
    "marks are missing": TicketCategory.MISSING_MARKS,
    "mark is missing": TicketCategory.MISSING_MARKS,
    "marks missing": TicketCategory.MISSING_MARKS,
    "marks not posted": TicketCategory.MISSING_MARKS,
    "grade missing": TicketCategory.MISSING_MARKS,
    "grade is missing": TicketCategory.MISSING_MARKS,
    "grades missing": TicketCategory.MISSING_MARKS,
    "grades are missing": TicketCategory.MISSING_MARKS,
    "results missing": TicketCategory.MISSING_MARKS,
    "feel unsafe": TicketCategory.HARASSMENT,
    "threatened": TicketCategory.HARASSMENT,
    "threatening": TicketCategory.HARASSMENT,
    "bullying": TicketCategory.HARASSMENT,
    "bullied": TicketCategory.HARASSMENT,
    "intimidation": TicketCategory.HARASSMENT,
    "intimidated": TicketCategory.HARASSMENT,
    "intimidating": TicketCategory.HARASSMENT,
    "intimidate": TicketCategory.HARASSMENT,
}

# Categories that auto-escalate to Critical/High priority
CRITICAL_CATEGORIES = {TicketCategory.HARASSMENT, TicketCategory.CORRUPTION, TicketCategory.ASSAULT}
HIGH_CATEGORIES = {TicketCategory.FEE_DISPUTE, TicketCategory.MISSING_MARKS}


def _check_sensitive_keywords(message: str) -> Optional[TicketCategory]:
    """Check message against trigger terms. Returns category if matched, None otherwise."""
    message_lower = message.lower()
    for term, category in SENSITIVE_TRIGGER_TERMS.items():
        if term in message_lower:
            return category
    return None


def _get_priority_for_category(category: TicketCategory) -> TicketPriority:
    """Auto-assign priority based on category."""
    if category in CRITICAL_CATEGORIES:
        return TicketPriority.CRITICAL
    if category in HIGH_CATEGORIES:
        return TicketPriority.HIGH
    if category == TicketCategory.FEEDBACK:
        return TicketPriority.LOW
    return TicketPriority.MEDIUM


async def _generate_tracking_id(db: AsyncSession) -> str:
    """Generate next sequential tracking ID like TKT-0001."""
    result = await db.execute(select(func.count(Ticket.id)))
    count = result.scalar() or 0
    return f"TKT-{count + 1:04d}"


async def _create_auto_ticket(
    db: AsyncSession,
    student_id: int,
    message: str,
    category: TicketCategory,
) -> tuple[Ticket, Optional[str]]:
    """Auto-create a ticket from a sensitive chat message with load balancing and queue position."""
    tracking_id = await _generate_tracking_id(db)
    priority = _get_priority_for_category(category)

    # Agent load balancing & queue position
    assigned_agent_id, assigned_agent_name, queue_pos = await find_least_loaded_agent(db)

    ticket = Ticket(
        tracking_id=tracking_id,
        student_id=student_id,
        category=category,
        subject=f"Auto-escalated: {category.value.replace('_', ' ').title()}",
        description=message,
        status=TicketStatus.OPEN,
        priority=priority,
        assigned_agent_id=assigned_agent_id,
        queue_position=queue_pos,
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)

    # Add system message
    system_msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type=SenderType.SYSTEM,
        message=f"Ticket auto-created from chat. Original message: {message}",
    )
    db.add(system_msg)
    await db.flush()

    return ticket, assigned_agent_name


async def _search_nav_node(db: AsyncSession, location_query: str) -> Optional[Dict[str, Any]]:
    """Search for a navigation node by name or synonyms."""
    query_lower = location_query.lower().strip()

    result = await db.execute(select(NavNode))
    nodes = result.scalars().all()

    best_match = None
    best_score = 0.0

    for node in nodes:
        # Check exact name match
        if node.name.lower() == query_lower:
            return {
                "id": node.id,
                "name": node.name,
                "panoee_scene_id": node.panoee_scene_id,
                "description": node.description,
                "building": node.building,
                "floor": node.floor,
            }

        # Check synonym match
        for synonym in (node.synonyms or []):
            if synonym.lower() == query_lower or synonym.lower() in query_lower or query_lower in synonym.lower():
                return {
                    "id": node.id,
                    "name": node.name,
                    "panoee_scene_id": node.panoee_scene_id,
                    "description": node.description,
                    "building": node.building,
                    "floor": node.floor,
                }

        # Partial name match scoring
        if query_lower in node.name.lower() or node.name.lower() in query_lower:
            score = len(query_lower) / max(len(node.name), len(query_lower))
            if score > best_score:
                best_score = score
                best_match = {
                    "id": node.id,
                    "name": node.name,
                    "panoee_scene_id": node.panoee_scene_id,
                    "description": node.description,
                    "building": node.building,
                    "floor": node.floor,
                }

    return best_match if best_score > 0.3 else None


async def _get_ticket_status(db: AsyncSession, student_id: int, ticket_ref: Optional[str] = None) -> Optional[Dict]:
    """Look up ticket status for a student."""
    if ticket_ref:
        # Extract ticket ID pattern (TKT-XXXX)
        match = re.search(r'TKT-\d+', ticket_ref.upper())
        if match:
            tracking_id = match.group()
            result = await db.execute(
                select(Ticket).where(
                    Ticket.tracking_id == tracking_id,
                    Ticket.student_id == student_id,
                )
            )
            ticket = result.scalar_one_or_none()
            if ticket:
                return {
                    "tracking_id": ticket.tracking_id,
                    "subject": ticket.subject,
                    "status": ticket.status.value,
                    "priority": ticket.priority.value,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat(),
                }

    # If no specific ticket, get the most recent one
    result = await db.execute(
        select(Ticket)
        .where(Ticket.student_id == student_id)
        .order_by(Ticket.created_at.desc())
        .limit(1)
    )
    ticket = result.scalar_one_or_none()
    if ticket:
        return {
            "tracking_id": ticket.tracking_id,
            "subject": ticket.subject,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
        }

    return None


async def _get_or_create_session(db: AsyncSession, student_id: int, session_id: Optional[int]) -> ChatSession:
    """Get existing chat session or get the student's latest active session, or create a new one."""
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.student_id == student_id,
            )
        )
        session = result.scalar_one_or_none()
        if session:
            session.updated_at = datetime.now(timezone.utc)
            return session

    # Check for latest active session
    res = await db.execute(
        select(ChatSession)
        .where(ChatSession.student_id == student_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(1)
    )
    latest_session = res.scalar_one_or_none()
    if latest_session:
        latest_session.updated_at = datetime.now(timezone.utc)
        return latest_session

    # Create new session
    session = ChatSession(student_id=student_id)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def _get_chat_history(db: AsyncSession, session_id: int, limit: int = 10) -> List[Dict]:
    """Get recent chat messages for context."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return [{"role": msg.role, "content": msg.content} for msg in reversed(messages)]


async def process_message(
    db: AsyncSession,
    student_id: int,
    message: str,
    session_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main orchestrator — processes a student chat message and returns a response.
    """
    # Get/create session
    session = await _get_or_create_session(db, student_id, session_id)

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=message,
    )
    db.add(user_msg)
    await db.flush()

    # ─── Step 1: Keyword Safety Net ───────────────────────────
    forced_category = _check_sensitive_keywords(message)

    if forced_category:
        # Force sensitive route — bypass LLM classification
        intent = "sensitive"
        sensitive_category = forced_category.value
        confidence = 1.0
        clarify_question = None
        logger.info(f"Keyword safety net triggered: {forced_category.value}")
    else:
        # ─── Step 2: LLM Classification (Call 1) ─────────────
        history = await _get_chat_history(db, session.id)
        classification = await deepseek_service.classify_intent(message, history)

        # Check for LLM failure
        if classification.get("error"):
            # Try retrieved RAG chunks from ChromaDB first
            chunks = rag_service.query(message, n_results=3)
            if chunks:
                extracted = chunks[0]["content"]
                bot_msg = ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=extracted,
                    intent="faq",
                    metadata_json={"is_cached": True, "source": chunks[0].get("title")},
                )
                db.add(bot_msg)
                await db.flush()
                return {
                    "message": extracted,
                    "intent": "faq",
                    "confidence": 0.8,
                    "session_id": session.id,
                    "metadata": {"is_cached": True, "source": chunks[0].get("title")},
                    "is_fallback": True,
                }

            # Try cached answer as second resort
            cached = deepseek_service._find_cached_answer(message)
            if cached:
                bot_msg = ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=cached,
                    intent="faq",
                    metadata_json={"is_cached": True},
                )
                db.add(bot_msg)
                await db.flush()
                return {
                    "message": cached,
                    "intent": "faq",
                    "confidence": 0.7,
                    "session_id": session.id,
                    "metadata": {"is_cached": True},
                    "is_fallback": True,
                }

            # Full fallback
            fallback_msg = classification.get("fallback_message", "I'm having trouble connecting to my brain right now. You can try again in a moment, or create a support ticket.")
            bot_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=fallback_msg,
                intent="error",
            )
            db.add(bot_msg)
            await db.flush()
            return {
                "message": fallback_msg,
                "intent": "error",
                "confidence": 0.0,
                "session_id": session.id,
                "metadata": {"show_create_ticket": True},
                "is_fallback": True,
            }

        intent = classification.get("intent", "clarify")
        confidence = float(classification.get("confidence", 0.5))
        sensitive_category = classification.get("sensitive_category")
        clarify_question = classification.get("clarify_question")

    # ─── Step 3: Route by Intent (6-Way Flow) ─────────────────

    # 1. intent == "clarify" -> check if ChromaDB has a matching document first!
    if intent == "clarify":
        # Check if the knowledge base contains relevant information matching this query.
        # This ensures inquiries about uploaded CVs, personnel profiles, or specific documents
        # are never falsely blocked by the classifier.
        rag_probe = rag_service.query(message, n_results=4)
        has_strong_rag_match = rag_probe and any(c.get("score", 0) >= 0.35 for c in rag_probe)

        if has_strong_rag_match:
            logger.info("Clarify overruled by strong RAG match (score >= 0.35). Promoting to FAQ.")
            intent = "faq"
            confidence = 0.85
        else:
            clarify_text = clarify_question or "I want to make sure I understand correctly. Could you clarify — are you asking about campus policies, reporting an issue, looking for a location on campus, or checking on a ticket?"
            bot_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=clarify_text,
                intent="clarify",
            )
            db.add(bot_msg)
            await db.flush()
            return {
                "message": clarify_text,
                "intent": "clarify",
                "confidence": confidence,
                "session_id": session.id,
                "metadata": None,
                "is_fallback": False,
            }

    # 2. intent == "sensitive" -> skip Call 2 entirely, auto-create ticket, give tracking ID
    elif intent == "sensitive":
        ticket_cat = forced_category or _map_category_string(sensitive_category)
        ticket, agent_name = await _create_auto_ticket(db, student_id, message, ticket_cat)

        agent_line = f"👤 **Assigned Agent:** {agent_name}\n" if agent_name else ""
        queue_line = f"🔢 **Queue Position:** #{ticket.queue_position} in line\n" if ticket.queue_position else ""

        response_text = (
            f"I understand this is an important matter, and I want to make sure it's handled properly by our university support team.\n\n"
            f"📋 **Tracking ID:** {ticket.tracking_id}\n"
            f"📌 **Priority:** {ticket.priority.value.replace('_', ' ').title()}\n"
            f"📊 **Status:** Open\n"
            f"{agent_line}"
            f"{queue_line}\n"
            f"A human support agent has been assigned to your case. "
            f"You can monitor updates and reply in the **My Tickets** tab."
        )

        bot_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            intent="sensitive",
            metadata_json={
                "ticket_id": ticket.tracking_id,
                "ticket_db_id": ticket.id,
                "assigned_agent_name": agent_name,
                "queue_position": ticket.queue_position,
            },
        )
        db.add(bot_msg)

        # Mark session as escalated
        session.resolved_by = "ticket"
        await db.flush()

        return {
            "message": response_text,
            "intent": "sensitive",
            "confidence": confidence,
            "session_id": session.id,
            "metadata": {
                "ticket_id": ticket.tracking_id,
                "ticket_db_id": ticket.id,
                "priority": ticket.priority.value,
                "assigned_agent_name": agent_name,
                "queue_position": ticket.queue_position,
            },
            "is_fallback": False,
        }

    # 3. intent == "navigation" -> skip Call 2 entirely, return static pointer to Campus Map tab
    elif intent == "navigation":
        nav_node = await _search_nav_node(db, message)
        if nav_node:
            response_text = (
                f"For directions, head to the Campus Map tab — you'll find a searchable virtual tour there.\n\n"
                f"📍 **{nav_node['name']}**\n"
            )
            if nav_node.get("building"):
                response_text += f"🏢 Building: {nav_node['building']}\n"
            if nav_node.get("floor"):
                response_text += f"🔢 Floor: {nav_node['floor']}\n"
            if nav_node.get("description"):
                response_text += f"ℹ️ {nav_node['description']}\n"
            response_text += "\nOpen the Campus Map tab to view its exact interactive location."
            metadata = {
                "type": "nav_link",
                "node_id": nav_node["id"],
                "node_name": nav_node["name"],
                "panoee_scene_id": nav_node.get("panoee_scene_id"),
            }
        else:
            response_text = "For directions, head to the Campus Map tab — you'll find a searchable virtual tour there."
            metadata = None

        bot_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            intent="navigation",
            metadata_json=metadata,
        )
        db.add(bot_msg)
        await db.flush()

        return {
            "message": response_text,
            "intent": "navigation",
            "confidence": confidence,
            "session_id": session.id,
            "metadata": metadata,
            "is_fallback": False,
        }

    # 4. intent == "feedback" -> skip Call 2 entirely, log as feedback ticket (low priority), thank student
    elif intent == "feedback":
        ticket, agent_name = await _create_auto_ticket(db, student_id, message, TicketCategory.FEEDBACK)
        agent_line = f"👤 **Assigned Agent:** {agent_name}\n" if agent_name else ""
        queue_line = f"🔢 **Queue Position:** #{ticket.queue_position} in line\n" if ticket.queue_position else ""

        response_text = (
            f"Thank you for sharing your feedback! We appreciate your input on improving campus life.\n\n"
            f"📋 **Tracking ID:** {ticket.tracking_id}\n"
            f"{agent_line}"
            f"{queue_line}\n"
            f"Our campus administration team has logged your submission for review. You can track this in the **My Tickets** tab."
        )
        bot_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            intent="feedback",
            metadata_json={
                "ticket_id": ticket.tracking_id,
                "ticket_db_id": ticket.id,
                "assigned_agent_name": agent_name,
                "queue_position": ticket.queue_position,
            },
        )
        db.add(bot_msg)
        await db.flush()

        return {
            "message": response_text,
            "intent": "feedback",
            "confidence": confidence,
            "session_id": session.id,
            "metadata": {
                "ticket_id": ticket.tracking_id,
                "ticket_db_id": ticket.id,
                "assigned_agent_name": agent_name,
                "queue_position": ticket.queue_position,
            },
            "is_fallback": False,
        }

    # 5. intent == "ticket_status" -> skip Call 2 entirely, query ticket DB directly
    elif intent == "ticket_status":
        ticket_info = await _get_ticket_status(db, student_id, message)

        if ticket_info:
            response_text = (
                f"Here's the current status of your ticket:\n\n"
                f"📋 **Ticket:** {ticket_info['tracking_id']}\n"
                f"📝 **Subject:** {ticket_info['subject']}\n"
                f"📊 **Status:** {ticket_info['status'].replace('_', ' ').title()}\n"
                f"📌 **Priority:** {ticket_info['priority'].replace('_', ' ').title()}\n"
                f"📅 **Created:** {ticket_info['created_at'][:10]}\n"
                f"🔄 **Last Updated:** {ticket_info['updated_at'][:10]}\n\n"
                f"You can view complete updates and agent responses in the **My Tickets** tab."
            )
        else:
            response_text = (
                "You currently have no active or previous support tickets on your account. "
                "If you need help or want to raise an issue, you can submit one anytime from the **My Tickets** tab."
            )

        bot_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            intent="ticket_status",
            metadata_json=ticket_info,
        )
        db.add(bot_msg)
        await db.flush()

        return {
            "message": response_text,
            "intent": "ticket_status",
            "confidence": confidence,
            "session_id": session.id,
            "metadata": ticket_info,
            "is_fallback": False,
        }

    # 6. intent == "faq" -> only this intent triggers Call 2 (DeepSeek Generator)
    else:
        chunks = rag_service.query(message, n_results=5)
        context_texts = [c["content"] for c in chunks]
        history = await _get_chat_history(db, session.id)

        answer_result = await deepseek_service.generate_answer(message, context_texts, history)

        if answer_result.get("error"):
            response_text = answer_result.get("fallback_message", "I'm having trouble connecting to my knowledge base right now.")
            is_fallback = True
        else:
            response_text = answer_result["answer"]
            is_fallback = answer_result.get("is_cached", False)

        bot_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            intent="faq",
            metadata_json={"chunks_count": len(chunks), "is_cached": is_fallback},
        )
        db.add(bot_msg)
        await db.flush()

        return {
            "message": response_text,
            "intent": "faq",
            "confidence": confidence,
            "session_id": session.id,
            "metadata": {"chunks_count": len(chunks)},
            "is_fallback": is_fallback,
        }


def _map_category_string(category_str: Optional[str]) -> TicketCategory:
    """Map classifier category string to TicketCategory enum."""
    if not category_str:
        return TicketCategory.OTHER
    cat = category_str.lower().strip()
    mapping = {
        "fees": TicketCategory.FEE_DISPUTE,
        "fee": TicketCategory.FEE_DISPUTE,
        "fee_dispute": TicketCategory.FEE_DISPUTE,
        "missing_marks": TicketCategory.MISSING_MARKS,
        "marks": TicketCategory.MISSING_MARKS,
        "grades": TicketCategory.MISSING_MARKS,
        "harassment": TicketCategory.HARASSMENT,
        "conduct": TicketCategory.HARASSMENT,
        "corruption": TicketCategory.CORRUPTION,
        "bribe": TicketCategory.CORRUPTION,
        "bribery": TicketCategory.CORRUPTION,
        "assault": TicketCategory.ASSAULT,
        "violence": TicketCategory.ASSAULT,
        "academic": TicketCategory.ACADEMIC,
        "facility": TicketCategory.FACILITY,
        "feedback": TicketCategory.FEEDBACK,
        "general": TicketCategory.GENERAL,
        "other": TicketCategory.OTHER,
    }
    return mapping.get(cat, TicketCategory.OTHER)
