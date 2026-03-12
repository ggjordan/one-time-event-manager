"""Add requires_notes to event_task for custom tasks

Revision ID: e6f7a8b9c0d1
Revises: c5d6e7f8a9b0
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "e6f7a8b9c0d1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "event_task",
        sa.Column("requires_notes", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("event_task", "requires_notes")
