"""sync migration-built schema with the ORM models

A database built only from migrations 001-003 differed from one created by
Base.metadata.create_all(): chunks had no updated_at column (the Chunk model
selects it, so reads failed), the chunk -> document foreign key did not
cascade, and several columns the models treat as nullable were NOT NULL.

Every step is guarded so this is a no-op on databases that already match.

Revision ID: 004
Revises: 902bc76d113c
Create Date: 2026-10-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "902bc76d113c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Columns the models declare nullable but migration 001 created NOT NULL.
_RELAX_NOT_NULL = {
    "documents": ["pages", "word_count", "char_count", "ocr_used", "processing_time", "file_size"],
    "evaluation_runs": ["status"],
    "traces": [
        "confidence_before_rewrite",
        "retrieval_attempts",
        "contradiction_detected",
        "clarification_needed",
        "final_confidence",
        "final_confidence_level",
    ],
}


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    insp = _inspector()

    if "updated_at" not in {c["name"] for c in insp.get_columns("chunks")}:
        op.add_column("chunks", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()))

    for table, columns in _RELAX_NOT_NULL.items():
        if not insp.has_table(table):
            continue
        by_name = {c["name"]: c for c in insp.get_columns(table)}
        for column in columns:
            if column in by_name and not by_name[column]["nullable"]:
                op.alter_column(table, column, nullable=True)

    for fk in insp.get_foreign_keys("chunks"):
        is_document_fk = fk["referred_table"] == "documents" and fk["constrained_columns"] == ["document_id"]
        if is_document_fk and (fk.get("options") or {}).get("ondelete") != "CASCADE":
            op.drop_constraint(fk["name"], "chunks", type_="foreignkey")
            op.create_foreign_key(fk["name"], "chunks", "documents", ["document_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    # The upgrade only aligns the schema with the models; reverting it would re-introduce
    # the mismatch, so downgrade is intentionally a no-op.
    pass
