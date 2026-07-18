import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    original_path = Column(String(500), nullable=True)
    extracted_text_path = Column(String(500), nullable=True)

    pages = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    ocr_used = Column(Boolean, default=False)
    language = Column(String(10), nullable=True)
    processing_time = Column(Float, default=0.0)
    file_size = Column(Integer, default=0)
    text_content = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
