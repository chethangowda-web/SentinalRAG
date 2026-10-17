import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
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
from app.models.password_reset import PasswordReset
from app.models.trace import Trace
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.email_service import EmailError, send_email
from app.services.qdrant_service import delete_document_vectors

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

_register_attempts = SlidingWindowCounter(settings.REGISTER_LIMIT_PER_HOUR, 3600)
_login_failures_by_ip = SlidingWindowCounter(settings.LOGIN_FAILURES_PER_10_MIN, 600)
_login_failures_by_email = SlidingWindowCounter(settings.LOGIN_FAILURES_PER_10_MIN, 600)
_reset_requests_by_ip = SlidingWindowCounter(10, 3600)
_reset_requests_by_email = SlidingWindowCounter(3, 3600)
_reset_attempts_by_ip = SlidingWindowCounter(20, 3600)


def reset_rate_limits() -> None:
    """Forget all counters (used by tests)."""
    for limiter in (
        _register_attempts, _login_failures_by_ip, _login_failures_by_email,
        _reset_requests_by_ip, _reset_requests_by_email, _reset_attempts_by_ip,
    ):
        limiter._events.clear()


def _client_ip(request: Request) -> str:
    # Behind Railway's proxy this is the real client address because uvicorn runs with --proxy-headers.
    return request.client.host if request.client else "unknown"


@router.get("/auth/config")
async def auth_config():
    """Public: lets the sign-up form know whether an invite code is needed."""
    return {
        "registration_requires_code": bool(settings.REGISTRATION_CODE),
        "password_reset_available": settings.email_enabled,
    }


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
    token = create_access_token(user.id, user.token_version or 0)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, name=user.name, email=user.email, created_at=user.created_at),
    )


def _hash_reset_token(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # the DateTime columns are naive UTC


@router.post("/auth/forgot-password", status_code=202)
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Email a single-use reset link. The answer is the same whether or not the address has an account."""
    if not settings.email_enabled:
        raise AppException(
            status_code=503,
            detail="Password reset by email is not set up on this server. Ask the administrator to reset your password.",
        )
    ip = _client_ip(request)
    _reset_requests_by_ip.enforce(ip, "Too many reset requests from this address. Try again later.")
    _reset_requests_by_email.enforce(body.email, "Too many reset requests for this account. Try again later.")
    _reset_requests_by_ip.record(ip)
    _reset_requests_by_email.record(body.email)

    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user:
        secret = secrets.token_urlsafe(32)
        db.add(PasswordReset(
            user_id=user.id,
            token_hash=_hash_reset_token(secret),
            expires_at=_utcnow() + timedelta(minutes=settings.PASSWORD_RESET_MINUTES),
        ))
        await db.commit()
        base = settings.PUBLIC_URL.rstrip("/") or str(request.base_url).rstrip("/")
        link = f"{base}/reset-password/?token={secret}"
        text = (
            f"Hello {user.name},\n\n"
            f"Someone asked to reset the password of your SentinelRAG account. Open this link to choose a new one "
            f"(it works once and expires in {settings.PASSWORD_RESET_MINUTES} minutes):\n\n{link}\n\n"
            "If you did not ask for this, ignore this email: your password stays as it is."
        )
        try:
            await send_email(user.email, "Reset your SentinelRAG password", text)
        except EmailError as exc:  # never tell the caller: that would reveal which addresses have accounts
            logger.error("Could not send the password reset email: %s", exc)
    return {"message": "If an account exists for that email, a reset link is on its way."}


@router.post("/auth/reset-password", status_code=204)
async def reset_password(body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    _reset_attempts_by_ip.enforce(ip, "Too many attempts. Try again later.")
    _reset_attempts_by_ip.record(ip)

    reset = (await db.execute(
        select(PasswordReset).where(
            PasswordReset.token_hash == _hash_reset_token(body.token.strip()),
            PasswordReset.used_at.is_(None),
            PasswordReset.expires_at > _utcnow(),
        )
    )).scalar_one_or_none()
    if reset is None:
        raise AppException(status_code=400, detail="This reset link is invalid or has expired. Request a new one.")

    user = (await db.execute(select(User).where(User.id == reset.user_id))).scalar_one()
    user.password_hash = hash_password(body.password)
    user.token_version = (user.token_version or 0) + 1  # signs the account out everywhere
    reset.used_at = _utcnow()
    await db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None)))
    await db.commit()
    _login_failures_by_email.reset(user.email)


@router.post("/auth/change-password", response_model=TokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the password; every other device is signed out, this one gets a fresh token."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise AppException(status_code=403, detail="Your current password is not correct")
    current_user.password_hash = hash_password(body.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(current_user.id, current_user.token_version),
        user=UserResponse(id=current_user.id, name=current_user.name, email=current_user.email, created_at=current_user.created_at),
    )


@router.post("/auth/logout-everywhere", status_code=204)
async def logout_everywhere(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """End every session of this account, including this one (e.g. after losing a device)."""
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.commit()


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
    await db.execute(delete(PasswordReset).where(PasswordReset.user_id == user_id))
    await db.execute(delete(DocumentEvaluation).where(DocumentEvaluation.user_id == user_id))
    await db.execute(delete(EvaluationRun).where(EvaluationRun.user_id == user_id))
    if doc_ids:
        await db.execute(delete(DocumentEvaluation).where(DocumentEvaluation.document_id.in_(doc_ids)))
        await db.execute(delete(Chunk).where(Chunk.document_id.in_(doc_ids)))
    await db.execute(delete(Document).where(Document.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    logger.info("Account deleted: %s (%d documents)", user_id, len(doc_ids))
