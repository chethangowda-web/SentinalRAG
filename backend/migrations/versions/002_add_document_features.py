"""add document features columns (ocr_quality, summary, duplicate, etc.)

Revision ID: 002
Revises: 001
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("ocr_quality", sa.String(10), nullable=True))
    op.add_column("documents", sa.Column("ocr_confidence", sa.Float(), nullable=True))
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("key_topics", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("keywords", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("entities", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("document_type", sa.String(50), nullable=True))
    op.add_column("documents", sa.Column("estimated_reading_time", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("sha256_hash", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("duplicate_of", sa.String(36), nullable=True))
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"])


def downgrade() -> None:
    op.drop_index("ix_documents_sha256_hash")
    op.drop_column("documents", "duplicate_of")
    op.drop_column("documents", "sha256_hash")
    op.drop_column("documents", "estimated_reading_time")
    op.drop_column("documents", "document_type")
    op.drop_column("documents", "entities")
    op.drop_column("documents", "keywords")
    op.drop_column("documents", "key_topics")
    op.drop_column("documents", "summary")
    op.drop_column("documents", "ocr_confidence")
    op.drop_column("documents", "ocr_quality")
