"""Dashboard + JSON API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pokebargain.config import Settings
from pokebargain.db.base import Database
from pokebargain.db.repository import ListingRepository, ScanRepository
from pokebargain.factory import (
    build_ebay_client,
    build_tcg_client,
    build_vision,
)
from pokebargain.pipeline.scan import ScanPipeline
from pokebargain.web.deps import get_db_session, get_settings_dep

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    sort: str = "score",
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
) -> Any:
    repo = ListingRepository(session)
    opportunities = repo.list_opportunities(
        min_score=settings.min_opportunity_score, sort=sort, limit=100
    )
    scans = ScanRepository(session).recent(5)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "opportunities": opportunities,
            "sort": sort,
            "min_score": settings.min_opportunity_score,
            "scans": scans,
        },
    )


@router.get("/listings/{listing_id}", response_class=HTMLResponse)
def listing_detail(
    listing_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
) -> Any:
    listing = ListingRepository(session).get(listing_id)
    if listing is None:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        request, "listing.html", {"listing": listing}
    )


@router.post("/scan")
def trigger_scan(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
) -> RedirectResponse:
    database: Database = request.app.state.database
    pipeline = ScanPipeline(
        settings,
        database,
        build_ebay_client(settings),
        build_tcg_client(settings),
        build_vision(settings),
    )
    pipeline.run()
    return RedirectResponse("/", status_code=303)


@router.get("/api/opportunities")
def api_opportunities(
    sort: str = "score",
    min_score: float | None = None,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
) -> list[dict[str, Any]]:
    repo = ListingRepository(session)
    rows = repo.list_opportunities(
        min_score=min_score if min_score is not None else settings.min_opportunity_score,
        sort=sort,
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "card_name": r.card_name,
            "set_name": r.set_name,
            "ebay_price": float(r.price),
            "market_value": float(r.market_value) if r.market_value is not None else None,
            "opportunity_score": r.opportunity_score,
            "discount_pct": r.discount_pct,
            "potential_profit": float(r.potential_profit)
            if r.potential_profit is not None
            else None,
            "listing_url": r.listing_url,
            "image_url": r.card_image_url or r.image_url,
            "found_at": r.found_at.isoformat() if r.found_at else None,
            "match_method": r.match_method,
        }
        for r in rows
    ]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
