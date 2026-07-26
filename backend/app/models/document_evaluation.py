import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class DocumentEvaluation(Base):
    __tablename__ = "document_evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    overall_score = Column(Float, default=0.0)
    faithfulness = Column(Float, default=0.0)
    correctness = Column(Float, default=0.0)
    answer_relevancy = Column(Float, default=0.0)
    context_recall = Column(Float, default=0.0)
    precision = Column(Float, default=0.0)
    hallucination_rate = Column(Float, default=0.0)
    retrieval_score = Column(Float, default=0.0)
    ocr_confidence = Column(Float, nullable=True)
    processing_time = Column(Float, default=0.0)

    total_questions = Column(Integer, default=0)
    eval_data = Column(Text, nullable=True)

    status = Column(String(20), default="running")
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
