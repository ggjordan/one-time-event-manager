"""EventTask status: not_started -> incomplete

Revision ID: a1b2c3d4e5f6
Revises: 4b5210fe5ff2
Create Date: 2026-03-11

"""
from alembic import op


revision = "a1b2c3d4e5f6"
down_revision = "4b5210fe5ff2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE event_task SET status = 'incomplete' WHERE status = 'not_started'")


def downgrade():
    op.execute("UPDATE event_task SET status = 'not_started' WHERE status = 'incomplete'")

