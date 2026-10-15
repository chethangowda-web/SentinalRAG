import hmac
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user, hash_password, verify_password
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.ratelimit import SlidingWindowCounter
from app.models.chat_session import ChatMessage, ChatSession
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.document_evaluation import DocumentEvaluation
from app.models.evaluation_run import EvaluationRun
from app.models.trace import Trace
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.qdrant_service import delete_document_vectors

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

_register_attempts = SlidingWindowCounter(settings.REGISTER_LIMIT_PER_HOUR, 3600)
_login_failures_by_ip = SlidingWindowCounter(settings.LOGIN_FAILURES_PER_10_MIN, 600)
_login_failures_by_email = SlidingWindowCounter(settings.LOGIN_FAILURES_PER_10_MIN, 600)


def reset_rate_limits() -> None:
    """Forget all counters (used by tests)."""
    for limiter in (_register_attempts, _login_failures_by_ip, _login_failures_by_email):
        limiter._events.clear()


def _client_ip(request: Request) -> str:
    # Behind Railway's proxy this is the real client address because uvicorn runs with --proxy-headers.
    return request.client.host if request.client else "unknown"


@router.get("/auth/config")
async def auth_config():
    """Public: lets the sign-up form know whether an invite code is needed."""
    return {"registration_requires_code": bool(settings.REGISTRATION_CODE)}


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    _register_attempts.enforce(ip, "Too many sign-ups from this address.")
    _register_attempts.record(ip)

    if settings.REGISTRATION_CODE and not hmac.compare_digest(
        (body.invite_code or "").encode(), settings.REGISTRATION_CODE.encode()
    ):
        raise AppException(status_code=403, detail="A valid invite code is required to create an account.")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, name=user.name, email=user.email, created_at=user.created_at),
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    _login_failures_by_ip.enforce(ip, "Too many failed sign-in attempts.")
    _login_failures_by_email.enforce(body.email, "Too many failed sign-in attempts for this account.")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        _login_failures_by_ip.record(ip)
        _login_failures_by_email.record(body.email)
        raise AppException(status_code=401, detail="Invalid email or password")

    _login_failures_by_email.reset(body.email)
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, name=user.name, email=user.email, created_at=user.created_at),
    )


@router.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}


@router.get("/auth/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_count = await db.execute(select(func.count(Document.id)).where(Document.user_id == current_user.id))
    session_count = await db.execute(select(func.count(ChatSession.id)).where(ChatSession.user_id == current_user.id))
    eval_count = await db.execute(select(func.count(EvaluationRun.id)).where(EvaluationRun.user_id == current_user.id))

    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        created_at=current_user.created_at,
        total_documents=doc_count.scalar() or 0,
        total_sessions=session_count.scalar() or 0,
        total_evaluations=eval_count.scalar() or 0,
        is_admin=current_user.email.lower() in settings.admin_emails,
    )


class DeleteAccountRequest(BaseModel):
    password: str


@router.delete("/auth/me", status_code=204)
async def delete_account(
    body: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete the account and everything it owns (documents, vectors, chats, traces)."""
    if not verify_password(body.password, current_user.password_hash):
        raise AppException(status_code=403, detail="Incorrect password")

    user_id = current_user.id
    docs = (await db.execute(select(Document).where(Document.user_id == user_id))).scalars().all()
    doc_ids = [d.id for d in docs]

    for doc in docs:
        try:
            delete_document_vectors(doc.id)
        except Exception as exc:  # the account must still be deletable if Qdrant is down
            logger.warning("Could not delete vectors for %s: %s", doc.id, exc)
        for path_str in (doc.original_path, doc.extracted_text_path):
            if path_str:
                Path(path_str).unlink(missing_ok=True)

    session_ids = select(ChatSession.id).where(ChatSession.user_id == user_id)
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(session_ids)))
    await db.execute(delete(ChatSession).where(ChatSession.user_id == user_id))
    await db.execute(delete(Trace).where(Trace.user_id == user_id))
    await db.execute(delete(DocumentEvaluation).where(DocumentEvaluation.user_id == user_id))
    await db.execute(delete(EvaluationRun).where(EvaluationRun.user_id == user_id))
    if doc_ids:
        await db.execute(delete(DocumentEvaluation).where(DocumentEvaluation.document_id.in_(doc_ids)))
        await db.execute(delete(Chunk).where(Chunk.document_id.in_(doc_ids)))
    await db.execute(delete(Document).where(Document.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    logger.info("Account deleted: %s (%d documents)", user_id, len(doc_ids))
