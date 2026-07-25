import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func

from app.core.database import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(20), default="running")
    created_at = Column(DateTime, server_default=func.now())
