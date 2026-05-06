"""Merchant-category learning: record user corrections and look them up before AI parsing."""
import logging

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.merchant_override import MerchantOverride

logger = logging.getLogger(__name__)


def _normalize(merchant: str) -> str:
    """Lowercase and strip the merchant name for consistent lookup."""
    return merchant.lower().strip()


async def get_override(merchant: str, session: AsyncSession) -> str | None:
    """Return the user-learned category for a merchant, or None if not known."""
    key = _normalize(merchant)
    result = await session.execute(
        select(MerchantOverride).where(MerchantOverride.merchant_key == key)
    )
    row = result.scalar_one_or_none()
    if row:
        logger.info("Merchant override found: %r → %r", key, row.category)
    return row.category if row else None


async def record_override(merchant: str, category: str, session: AsyncSession) -> None:
    """Upsert a merchant-to-category mapping. Increments count on repeat corrections."""
    key = _normalize(merchant)
    stmt = (
        insert(MerchantOverride)
        .values(merchant_key=key, category=category, count=1, last_used_at=func.now())
        .on_conflict_do_update(
            index_elements=["merchant_key"],
            set_={
                "category": category,
                "count": MerchantOverride.count + 1,
                "last_used_at": func.now(),
            },
        )
    )
    await session.execute(stmt)
    logger.info("Recorded merchant override: %r → %r", key, category)
