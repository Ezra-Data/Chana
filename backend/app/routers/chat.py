from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatMessageRequest, ChatBotResponse, ChatSessionResponse, ChatMessageHistory
from app.middleware.auth import get_current_user
from app.services import chat_service
from app.models.chat import ChatSession, ChatMessage
from sqlalchemy import select, func

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/message", response_model=ChatBotResponse)
async def send_message(
    data: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process a chat message through the AI orchestrator."""
    result = await chat_service.process_message(
        db=db,
        student_id=current_user.id,
        message=data.message,
        session_id=data.session_id,
    )

    return ChatBotResponse(
        message=result["message"],
        intent=result.get("intent"),
        confidence=result.get("confidence"),
        session_id=result["session_id"],
        metadata=result.get("metadata"),
        is_fallback=result.get("is_fallback", False),
    )


@router.get("/history")
async def get_active_chat_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the student's most recent chat session with messages.
    Does NOT auto-create a session — new users will get empty history.
    """
    # Find most recent session that has at least one message
    subq = select(ChatMessage.session_id).where(
        ChatMessage.session_id == ChatSession.id
    ).limit(1).correlate(ChatSession)

    res = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.student_id == current_user.id,
            subq.exists(),
        )
        .order_by(ChatSession.updated_at.desc())
        .limit(1)
    )
    session = res.scalar_one_or_none()
    if not session:
        # New user or no chats yet — return empty, don't create a session
        return {"session_id": None, "messages": []}

    # Fetch messages
    msg_res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.timestamp.asc())
    )
    messages = msg_res.scalars().all()

    return {
        "session_id": session.id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "metadata": m.metadata_json,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/new-session")
async def create_new_chat_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a fresh chat session on demand."""
    session = ChatSession(student_id=current_user.id)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return {"session_id": session.id, "messages": []}


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all chat sessions for the current student that have at least one message."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.student_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()

    response = []
    for session in sessions:
        # Count messages
        msg_count = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session.id)
        )
        count = msg_count.scalar() or 0

        # Skip empty sessions — no point showing them in Past Chats
        if count == 0:
            continue

        # Get preview from first user message
        first_user_msg = await db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.session_id == session.id, ChatMessage.role == "user")
            .order_by(ChatMessage.timestamp.asc())
            .limit(1)
        )
        preview_text = first_user_msg.scalar_one_or_none()

        resp = ChatSessionResponse.model_validate(session)
        resp.message_count = count
        resp.preview = (preview_text[:60] + "...") if preview_text and len(preview_text) > 60 else preview_text
        response.append(resp)

    return response


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageHistory])
async def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a chat session."""
    # Verify session belongs to user
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.student_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        return []

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    messages = result.scalars().all()
    return [ChatMessageHistory.model_validate(msg) for msg in messages]


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages (student only, own sessions)."""
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.student_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete all messages first (FK constraint)
    msgs = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    for msg in msgs.scalars().all():
        await db.delete(msg)

    await db.delete(session)
    await db.flush()

