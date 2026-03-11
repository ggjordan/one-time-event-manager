"""Add requires_drive_link to task_template (asset tasks only)

Revision ID: c5d6e7f8a9b0
Revises: b2c3d4e5f6a7
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a9b0"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Add column if not present (e.g. after a previous failed run)
    rows = conn.execute(sa.text("PRAGMA table_info(task_template)")).fetchall()
    cols = [row[1] for row in rows]
    if "requires_drive_link" not in cols:
        op.add_column(
            "task_template",
            sa.Column("requires_drive_link", sa.Boolean(), nullable=False, server_default="0"),
        )
    op.execute(sa.text('UPDATE task_template SET requires_drive_link = 1 WHERE "group" = \'assets\''))


def downgrade():
    op.drop_column("task_template", "requires_drive_link")
