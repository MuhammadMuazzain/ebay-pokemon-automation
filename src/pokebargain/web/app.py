"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pokebargain.config import Settings, get_settings
from pokebargain.factory import (
    build_database,
    build_ebay_client,
    build_tcg_client,
    build_vision,
)
from pokebargain.logging import get_logger
from pokebargain.pipeline.scan import ScanPipeline
from pokebargain.scanner.background import BackgroundScanner
from pokebargain.web.routes import router

log = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    if settings.database_url.startswith("sqlite"):
        Path("data").mkdir(exist_ok=True)

    database = build_database(settings)
    database.create_all()

    scanner_holder: dict[str, BackgroundScanner | None] = {"scanner": None}

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.auto_scan and settings.ebay_client_id and settings.ebay_client_secret:
            try:
                pipeline = ScanPipeline(
                    settings,
                    database,
                    build_ebay_client(settings),
                    build_tcg_client(settings),
                    build_vision(settings),
                )
                scanner = BackgroundScanner(pipeline, settings.scan_interval_seconds)
                scanner.start()
                scanner_holder["scanner"] = scanner
            except Exception:
                log.exception("Could not start background scanner")
        yield
        if scanner_holder["scanner"] is not None:
            scanner_holder["scanner"].stop()

    app = FastAPI(
        title="PokéBargain",
        description="Hidden bargain finder for Pokémon TCG listings on eBay UK",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.include_router(router)

    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app
