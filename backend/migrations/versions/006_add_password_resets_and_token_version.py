"""password reset links and revocable sessions

users.token_version is stored in every access token; changing it signs a user out of every device.
password_resets holds single-use reset links (hashed).

Revision ID: 006
Revises: 005
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    if "token_version" not in {c["name"] for c in _inspector().get_columns("users")}:
        op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    if not _inspector().has_table("password_resets"):
        op.create_table(
            "password_resets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
        op.create_index("ix_password_resets_token_hash", "password_resets", ["token_hash"], unique=True)


def downgrade() -> None:
    if _inspector().has_table("password_resets"):
        op.drop_table("password_resets")
    if "token_version" in {c["name"] for c in _inspector().get_columns("users")}:
        op.drop_column("users", "token_version")
