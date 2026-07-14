"""Web smoke tests with demo seed data."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pokebargain.config import Settings
from pokebargain.pipeline.scan import seed_demo_listings
from pokebargain.web.app import create_app


def test_dashboard_with_demo_seed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings = Settings(
        database_url=db_url,
        auto_scan=False,
        min_opportunity_score=75,
    )
    app = create_app(settings)
    seed_demo_listings(app.state.database)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hidden opportunity" in response.content
    assert b"Charizard" in response.content

    api = client.get("/api/opportunities")
    assert api.status_code == 200
    data = api.json()
    assert len(data) >= 1
    assert data[0]["opportunity_score"] >= 75

    assert client.get("/health").json()["status"] == "ok"
