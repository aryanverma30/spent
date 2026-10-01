"""Add budgets table for monthly per-category and overall spending limits.

Revision ID: 004
Revises: 003
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the budgets table."""
    op.create_table(
        "budgets",
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("monthly_limit", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("category"),
    )


def downgrade() -> None:
    """Drop the budgets table."""
    op.drop_table("budgets")
