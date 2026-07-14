"""ORM models for listings, identified cards, scan history, and opportunity scores."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Float, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from pokebargain.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Listing(Base):
    """An eBay UK listing that was discovered and analysed."""

    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("ebay_item_id", name="uq_ebay_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ebay_item_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    image_url: Mapped[str | None] = mapped_column(String(1000))
    listing_url: Mapped[str | None] = mapped_column(String(1000))
    condition: Mapped[str | None] = mapped_column(String(120))

    # Classification
    is_single_card: Mapped[bool] = mapped_column(default=True)
    filter_reason: Mapped[str | None] = mapped_column(String(200))

    # Identification
    card_name: Mapped[str | None] = mapped_column(String(200))
    set_name: Mapped[str | None] = mapped_column(String(200))
    card_number: Mapped[str | None] = mapped_column(String(50))
    language: Mapped[str | None] = mapped_column(String(40), default="English")
    rarity: Mapped[str | None] = mapped_column(String(80))
    estimated_condition: Mapped[str | None] = mapped_column(String(80))
    tcg_card_id: Mapped[str | None] = mapped_column(String(80))
    card_image_url: Mapped[str | None] = mapped_column(String(1000))

    match_method: Mapped[str | None] = mapped_column(String(40))  # fuzzy | vision
    match_confidence: Mapped[float | None] = mapped_column(Float)
    title_quality: Mapped[str | None] = mapped_column(String(40))

    # Market comparison
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    discount_pct: Mapped[float | None] = mapped_column(Float)
    potential_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Hidden bargain score (0–100)
    opportunity_score: Mapped[float | None] = mapped_column(Float, index=True)
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    search_term: Mapped[str | None] = mapped_column(String(120))
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class ScanRun(Base):
    """History of background / manual scan executions."""

    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    listings_fetched: Mapped[int] = mapped_column(Integer, default=0)
    listings_new: Mapped[int] = mapped_column(Integer, default=0)
    listings_scored: Mapped[int] = mapped_column(Integer, default=0)
    vision_calls: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="running")
    error: Mapped[str | None] = mapped_column(Text)
