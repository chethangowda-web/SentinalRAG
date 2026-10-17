import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func

from app.core.database import Base


class PasswordReset(Base):
    """A single-use password-reset link. Only the hash of the secret is stored, never the secret itself."""

    __tablename__ = "password_resets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
