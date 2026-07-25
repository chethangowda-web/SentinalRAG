"""add users table and user_id columns for multi-user support

Revision ID: 003
Revises: 002
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    conn = op.get_bind()
    return conn.dialect.has_table(conn, name)


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def _has_index(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # --- Users table ---
    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index("ix_users_email", "users", ["email"])
    else:
        if not _has_index("ix_users_email"):
            op.create_index("ix_users_email", "users", ["email"])

    # --- Chat sessions table (may already exist from create_all) ---
    if not _has_table("chat_sessions"):
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("title", sa.String(255), nullable=True, server_default="New Chat"),
            sa.Column("pinned", sa.Boolean(), nullable=True, server_default="false"),
            sa.Column("deleted", sa.Boolean(), nullable=True, server_default="false"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("message_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("last_message", sa.Text(), nullable=True),
            sa.Column("last_confidence_level", sa.String(10), nullable=True),
        )
    if not _has_index("ix_chat_sessions_user_id"):
        op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    # --- Chat messages table (may already exist from create_all) ---
    if not _has_table("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("session_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(10), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("response_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # --- User_id on documents ---
    if not _has_column("documents", "user_id"):
        op.execute("ALTER TABLE documents ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)")
    if not _has_index("ix_documents_user_id"):
        op.create_index("ix_documents_user_id", "documents", ["user_id"])

    # --- User_id on traces ---
    if not _has_column("traces", "user_id"):
        op.execute("ALTER TABLE traces ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)")
    if not _has_index("ix_traces_user_id"):
        op.create_index("ix_traces_user_id", "traces", ["user_id"])

    # --- Evaluation runs table (may already exist from create_all) ---
    if not _has_table("evaluation_runs"):
        op.create_table(
            "evaluation_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("evaluation_id", sa.String(100), nullable=False),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="running"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_evaluation_runs_evaluation_id", "evaluation_runs", ["evaluation_id"])
        op.create_index("ix_evaluation_runs_user_id", "evaluation_runs", ["user_id"])
    else:
        if not _has_index("ix_evaluation_runs_evaluation_id"):
            op.create_index("ix_evaluation_runs_evaluation_id", "evaluation_runs", ["evaluation_id"])
        if not _has_index("ix_evaluation_runs_user_id"):
            op.create_index("ix_evaluation_runs_user_id", "evaluation_runs", ["user_id"])

    # --- Backfill: assign existing orphan records to the first user ---
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1"))
    first_user = result.scalar()
    if first_user:
        conn.execute(
            sa.text("UPDATE documents SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": first_user},
        )
        conn.execute(
            sa.text("UPDATE chat_sessions SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": first_user},
        )
        conn.execute(
            sa.text("UPDATE traces SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": first_user},
        )
        conn.execute(
            sa.text("UPDATE evaluation_runs SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": first_user},
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_traces_user_id")
    op.execute("DROP INDEX IF EXISTS ix_chat_sessions_user_id")
    op.execute("DROP INDEX IF EXISTS ix_documents_user_id")
    op.execute("DROP INDEX IF EXISTS ix_evaluation_runs_user_id")
    op.execute("DROP INDEX IF EXISTS ix_evaluation_runs_evaluation_id")
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_session_id")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    for table in ("chat_messages", "chat_sessions", "evaluation_runs", "users"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for table in ("documents", "traces"):
        if _has_column(table, "user_id"):
            op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS user_id")
