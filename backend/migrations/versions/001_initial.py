"""create initial tables

Revision ID: 001
Revises:
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in _inspector().get_columns(table)}


def _has_index(table: str, name: str) -> bool:
    return name in {i["name"] for i in _inspector().get_indexes(table)}


def upgrade() -> None:
    # Guards make this safe on databases that were created from the models before Alembic was used.
    if not _has_table("documents"):
        _create_documents()
    if not _has_table("chunks"):
        _create_chunks()
    if not _has_table("traces"):
        _create_traces()


def _create_documents() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("original_path", sa.String(500), nullable=True),
        sa.Column("extracted_text_path", sa.String(500), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("processing_time", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def _create_chunks() -> None:
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("vector_id", sa.String(255), nullable=True),
        sa.Column("embedding_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])


def _create_traces() -> None:
    op.create_table(
        "traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("rewritten_query", sa.Text(), nullable=True),
        sa.Column("confidence_before_rewrite", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence_after_rewrite", sa.Float(), nullable=True),
        sa.Column("retrieval_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason_for_retry", sa.Text(), nullable=True),
        sa.Column("contradiction_detected", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("contradiction_reason", sa.Text(), nullable=True),
        sa.Column("clarification_needed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("clarification_question", sa.Text(), nullable=True),
        sa.Column("final_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("final_confidence_level", sa.String(10), nullable=False, server_default="LOW"),
        sa.Column("execution_path", sa.Text(), nullable=True),
        sa.Column("graph_execution", sa.Text(), nullable=True),
        sa.Column("retrieval_details", sa.Text(), nullable=True),
        sa.Column("confidence_breakdown", sa.Text(), nullable=True),
        sa.Column("llm_observability", sa.Text(), nullable=True),
        sa.Column("session_timeline", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("citations", sa.Text(), nullable=True),
        sa.Column("latencies", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("traces")
    op.drop_index("ix_chunks_document_id")
    op.drop_table("chunks")
    op.drop_table("documents")
