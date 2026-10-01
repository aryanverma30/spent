"""Add occurred_at to transactions so purchases can be backdated.

Existing rows are backfilled from created_at. The created_at indexes are
replaced with occurred_at equivalents because all period queries now filter
on occurred_at.

Revision ID: 003
Revises: 002
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add occurred_at, backfill it from created_at, and move the indexes over."""
    op.add_column(
        "transactions",
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.execute("UPDATE transactions SET occurred_at = created_at")
    op.alter_column("transactions", "occurred_at", nullable=False)

    op.drop_index("ix_transactions_category_created_at", table_name="transactions")
    op.drop_index("ix_transactions_created_at", table_name="transactions")
    op.create_index("ix_transactions_occurred_at", "transactions", ["occurred_at"])
    op.create_index(
        "ix_transactions_category_occurred_at",
        "transactions",
        ["category", "occurred_at"],
    )


def downgrade() -> None:
    """Drop occurred_at and restore the created_at indexes."""
    op.drop_index("ix_transactions_category_occurred_at", table_name="transactions")
    op.drop_index("ix_transactions_occurred_at", table_name="transactions")
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])
    op.create_index(
        "ix_transactions_category_created_at",
        "transactions",
        ["category", "created_at"],
    )
    op.drop_column("transactions", "occurred_at")
