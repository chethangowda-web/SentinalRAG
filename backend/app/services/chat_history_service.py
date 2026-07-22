import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import func as sqlfunc, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


### Session CRUD ###


async def create_session(db: AsyncSession, title: str = "New Chat", session_id: str | None = None) -> ChatSession:
    sid = session_id or str(uuid.uuid4())
    session = ChatSession(id=sid, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Chat session created: %s", session.id)
    return session


async def get_session(db: AsyncSession, session_id: str) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.deleted.is_(False))
    )
    return result.scalar_one_or_none()


async def update_session(
    db: AsyncSession, session_id: str, title: str | None = None, pinned: bool | None = None
) -> ChatSession | None:
    session = await get_session(db, session_id)
    if not session:
        return None
    if title is not None:
        session.title = title
    if pinned is not None:
        session.pinned = pinned
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session_id: str) -> bool:
    session = await get_session(db, session_id)
    if not session:
        return False
    session.deleted = True
    await db.commit()
    return True


async def list_sessions(
    db: AsyncSession, skip: int = 0, limit: int = 50, search: str | None = None
) -> list[ChatSession]:
    query = select(ChatSession).where(ChatSession.deleted.is_(False))
    if search:
        query = query.where(ChatSession.title.ilike(f"%{search}%"))
    query = query.order_by(ChatSession.pinned.desc(), desc(ChatSession.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_sessions(db: AsyncSession, search: str | None = None) -> int:
    query = select(sqlfunc.count(ChatSession.id)).where(ChatSession.deleted.is_(False))
    if search:
        query = query.where(ChatSession.title.ilike(f"%{search}%"))
    result = await db.execute(query)
    return result.scalar() or 0


### Message CRUD ###


async def add_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    response_json: dict | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        response_json=json.dumps(response_json) if response_json else None,
    )
    db.add(msg)

    session = await get_session(db, session_id)
    if session:
        session.message_count = (session.message_count or 0) + 1
        if role == "assistant" and response_json:
            session.last_message = content[:200] if content else None
            session.last_confidence_level = response_json.get("confidence_level")
        session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(
    db: AsyncSession, session_id: str, skip: int = 0, limit: int = 100
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_messages(db: AsyncSession, session_id: str) -> int:
    result = await db.execute(
        select(sqlfunc.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
    )
    return result.scalar() or 0


async def delete_all_messages(db: AsyncSession, session_id: str) -> None:
    await db.execute(
        ChatMessage.__table__.delete().where(ChatMessage.session_id == session_id)
    )
    session = await get_session(db, session_id)
    if session:
        session.message_count = 0
        session.last_message = None
        session.last_confidence_level = None
    await db.commit()


### Converters ###


def session_to_dict(s: ChatSession, message_count: int | None = None) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "pinned": s.pinned,
        "message_count": message_count if message_count is not None else (s.message_count or 0),
        "created_at": s.created_at.isoformat() if s.created_at else "",
        "updated_at": s.updated_at.isoformat() if s.updated_at else "",
        "last_message": s.last_message,
        "last_confidence_level": s.last_confidence_level,
    }


def message_to_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "response": json.loads(m.response_json) if m.response_json else None,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }
