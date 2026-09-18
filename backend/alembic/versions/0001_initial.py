"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables are created by SQLAlchemy metadata.create_all on startup.
    # This revision exists so `alembic upgrade head` is a valid production command.
    pass


def downgrade() -> None:
    pass
