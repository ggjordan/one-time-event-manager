"""Add notes, drive_link, due_weekday, requires_notes, task_template_game, status values

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("task_template", sa.Column("due_weekday", sa.Integer(), nullable=True))
    op.add_column("task_template", sa.Column("requires_notes", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("event_task", sa.Column("drive_link", sa.String(512), nullable=True))
    op.add_column("event_task", sa.Column("notes", sa.Text(), nullable=True))
    op.create_table(
        "task_template_game",
        sa.Column("task_template_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["game.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_template_id"], ["task_template.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_template_id", "game_id"),
    )


def downgrade():
    op.drop_table("task_template_game")
    op.drop_column("event_task", "notes")
    op.drop_column("event_task", "drive_link")
    op.drop_column("task_template", "requires_notes")
    op.drop_column("task_template", "due_weekday")
