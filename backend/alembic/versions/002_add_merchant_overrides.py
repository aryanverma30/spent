"""Add merchant_overrides table for NLP learning.

Revision ID: 002
Revises: 001
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the merchant_overrides table."""
    op.create_table(
        "merchant_overrides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("merchant_key", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("count", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "last_used_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_key", name="uq_merchant_overrides_merchant_key"),
    )
    op.create_index("ix_merchant_overrides_merchant_key", "merchant_overrides", ["merchant_key"])


def downgrade() -> None:
    """Drop the merchant_overrides table."""
    op.drop_index("ix_merchant_overrides_merchant_key", table_name="merchant_overrides")
    op.drop_table("merchant_overrides")
