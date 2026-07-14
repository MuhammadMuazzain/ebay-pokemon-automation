"""Compose services from settings."""

from __future__ import annotations

from pokebargain.config import Settings
from pokebargain.db.base import Database
from pokebargain.ebay.client import EbayClient
from pokebargain.ebay.oauth import AppTokenProvider
from pokebargain.tcg.client import PokemonTcgClient
from pokebargain.vision.openai_client import OpenAIVisionIdentifier


def build_database(settings: Settings) -> Database:
    return Database(settings.database_url)


def build_ebay_client(settings: Settings) -> EbayClient:
    provider = AppTokenProvider(settings)
    return EbayClient(settings.ebay_api_host, provider)


def build_tcg_client(settings: Settings) -> PokemonTcgClient:
    return PokemonTcgClient(settings)


def build_vision(settings: Settings) -> OpenAIVisionIdentifier | None:
    if not settings.openai_api_key:
        return None
    return OpenAIVisionIdentifier(settings)
