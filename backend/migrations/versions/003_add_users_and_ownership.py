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


def upgrade() -> None:
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

    op.add_column("documents", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.add_column("chat_sessions", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    op.add_column("traces", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("ix_traces_user_id", "traces", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_traces_user_id")
    op.drop_column("traces", "user_id")
    op.drop_index("ix_chat_sessions_user_id")
    op.drop_column("chat_sessions", "user_id")
    op.drop_index("ix_documents_user_id")
    op.drop_column("documents", "user_id")
    op.drop_index("ix_evaluation_runs_user_id")
    op.drop_index("ix_evaluation_runs_evaluation_id")
    op.drop_table("evaluation_runs")
    op.drop_index("ix_users_email")
    op.drop_table("users")
