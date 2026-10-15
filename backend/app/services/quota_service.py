"""Per-user limits that keep one account from exhausting storage or the (paid) LLM quota."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.chat_session import ChatMessage, ChatSession
from app.models.document import Document


async def check_upload_quota(db: AsyncSession, user_id: str, new_bytes: int) -> None:
    count, used = (await db.execute(
        select(func.count(Document.id), func.coalesce(func.sum(Document.file_size), 0)).where(Document.user_id == user_id)
    )).one()

    if count >= settings.MAX_DOCUMENTS_PER_USER:
        raise AppException(
            status_code=429,
            detail=f"Document limit reached ({settings.MAX_DOCUMENTS_PER_USER}). Delete a document to upload another.",
        )
    limit_bytes = settings.MAX_STORAGE_MB_PER_USER * 1024 * 1024
    if used + new_bytes > limit_bytes:
        raise AppException(
            status_code=429,
            detail=f"Storage limit reached ({settings.MAX_STORAGE_MB_PER_USER} MB). Delete a document to free space.",
        )


async def check_chat_quota(db: AsyncSession, user_id: str) -> None:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    used = (await db.execute(
        select(func.count(ChatMessage.id))
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == user_id, ChatMessage.role == "user", ChatMessage.created_at >= since)
    )).scalar() or 0

    if used >= settings.MAX_CHATS_PER_USER_PER_DAY:
        raise AppException(
            status_code=429,
            detail=f"Daily question limit reached ({settings.MAX_CHATS_PER_USER_PER_DAY} per 24 hours). Please try again later.",
        )
