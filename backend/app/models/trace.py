import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func

from app.core.database import Base


class Trace(Base):
    __tablename__ = "traces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    original_query = Column(Text, nullable=False)
    rewritten_query = Column(Text, nullable=True)
    confidence_before_rewrite = Column(Float, default=0.0)
    confidence_after_rewrite = Column(Float, default=0.0, nullable=True)
    retrieval_attempts = Column(Integer, default=1)
    reason_for_retry = Column(Text, nullable=True)
    contradiction_detected = Column(Boolean, default=False)
    contradiction_reason = Column(Text, nullable=True)
    clarification_needed = Column(Boolean, default=False)
    clarification_question = Column(Text, nullable=True)
    final_confidence = Column(Float, default=0.0)
    final_confidence_level = Column(String(10), default="LOW")
    execution_path = Column(Text, nullable=True)

    graph_execution = Column(Text, nullable=True)
    retrieval_details = Column(Text, nullable=True)
    confidence_breakdown = Column(Text, nullable=True)
    llm_observability = Column(Text, nullable=True)
    session_timeline = Column(Text, nullable=True)

    answer = Column(Text, nullable=True)
    citations = Column(Text, nullable=True)
    latencies = Column(Text, nullable=True)
