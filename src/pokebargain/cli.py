"""CLI entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import uvicorn

from pokebargain.config import get_settings
from pokebargain.factory import (
    build_database,
    build_ebay_client,
    build_tcg_client,
    build_vision,
)
from pokebargain.logging import get_logger
from pokebargain.pipeline.scan import ScanPipeline, seed_demo_listings

app = typer.Typer(help="PokéBargain — eBay UK Pokémon card bargain finder")
log = get_logger(__name__)


@app.command()
def init_db() -> None:
    """Create database tables."""
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        Path("data").mkdir(exist_ok=True)
    db = build_database(settings)
    db.create_all()
    typer.echo(f"Database ready: {settings.database_url}")


@app.command("seed-demo")
def seed_demo() -> None:
    """Load demo bargain rows for dashboard walkthrough without live API keys."""
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        Path("data").mkdir(exist_ok=True)
    db = build_database(settings)
    db.create_all()
    n = seed_demo_listings(db)
    typer.echo(f"Seeded {n} demo opportunities")


@app.command()
def scan(limit: int = typer.Option(40, help="Listings per search term")) -> None:
    """Run one broad eBay UK scan cycle."""
    settings = get_settings()
    db = build_database(settings)
    db.create_all()
    pipeline = ScanPipeline(
        settings,
        db,
        build_ebay_client(settings),
        build_tcg_client(settings),
        build_vision(settings),
    )
    counts = pipeline.run(limit_per_query=limit)
    typer.echo(f"Scan complete: {counts}")


@app.command()
def serve(
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: bool = False,
) -> None:
    """Start the bargain dashboard (and optional background scanner)."""
    settings = get_settings()
    uvicorn.run(
        "pokebargain.web.app:create_app",
        factory=True,
        host=host or settings.host,
        port=port or settings.port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
