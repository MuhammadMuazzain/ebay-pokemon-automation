"""Repository helpers for listings and scan history."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from pokebargain.db.models import Listing, ScanRun


class ListingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_ebay_id(self, ebay_item_id: str) -> Listing | None:
        return self._session.scalar(
            select(Listing).where(Listing.ebay_item_id == ebay_item_id)
        )

    def exists(self, ebay_item_id: str) -> bool:
        return self.get_by_ebay_id(ebay_item_id) is not None

    def add(self, listing: Listing) -> Listing:
        self._session.add(listing)
        self._session.flush()
        return listing

    def list_opportunities(
        self,
        *,
        min_score: float = 0.0,
        sort: str = "score",
        limit: int = 100,
    ) -> list[Listing]:
        stmt: Select[tuple[Listing]] = (
            select(Listing)
            .where(Listing.is_single_card.is_(True))
            .where(Listing.opportunity_score.is_not(None))
            .where(Listing.opportunity_score >= min_score)
        )
        order = {
            "score": desc(Listing.opportunity_score),
            "discount": desc(Listing.discount_pct),
            "profit": desc(Listing.potential_profit),
            "newest": desc(Listing.found_at),
        }.get(sort, desc(Listing.opportunity_score))
        stmt = stmt.order_by(order).limit(limit)
        return list(self._session.scalars(stmt))

    def get(self, listing_id: int) -> Listing | None:
        return self._session.get(Listing, listing_id)


class ScanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def start(self) -> ScanRun:
        run = ScanRun(status="running")
        self._session.add(run)
        self._session.flush()
        return run

    def finish(
        self,
        run: ScanRun,
        *,
        status: str = "completed",
        error: str | None = None,
        **counts: Any,
    ) -> ScanRun:
        run.finished_at = datetime.now(UTC)
        run.status = status
        run.error = error
        for key, value in counts.items():
            if hasattr(run, key):
                setattr(run, key, value)
        self._session.flush()
        return run

    def recent(self, limit: int = 20) -> list[ScanRun]:
        stmt = select(ScanRun).order_by(desc(ScanRun.started_at)).limit(limit)
        return list(self._session.scalars(stmt))
