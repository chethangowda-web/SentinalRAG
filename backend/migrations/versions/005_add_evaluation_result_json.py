"""keep evaluation results in the database

The report used to live only in a file inside the container, so every deploy erased it and the
Evaluation page went back to "No evaluation data".

Revision ID: 005
Revises: 004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("evaluation_runs", "result_json"):
        op.add_column("evaluation_runs", sa.Column("result_json", sa.Text(), nullable=True))


def downgrade() -> None:
    if _has_column("evaluation_runs", "result_json"):
        op.drop_column("evaluation_runs", "result_json")
