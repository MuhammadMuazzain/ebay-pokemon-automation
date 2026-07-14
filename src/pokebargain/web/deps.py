"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from pokebargain.config import Settings
from pokebargain.db.base import Database


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_db_session(db: Database = Depends(get_database)) -> Iterator[Session]:
    with db.session() as session:
        yield session
