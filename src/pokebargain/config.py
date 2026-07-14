"""Application configuration loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets must never be hardcoded."""

    model_config = SettingsConfigDict(
        env_prefix="POKEBARGAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # eBay Browse API (application credentials — Client ID / Secret)
    ebay_client_id: SecretStr | None = None
    ebay_client_secret: SecretStr | None = None
    ebay_marketplace_id: str = "EBAY_GB"
    ebay_api_host: str = "api.ebay.com"

    # Pokémon TCG API — https://pokemontcg.io/
    pokemon_tcg_api_key: SecretStr | None = None
    pokemon_tcg_base_url: str = "https://api.pokemontcg.io/v2"

    # OpenAI Vision — only used when fuzzy confidence is below threshold
    openai_api_key: SecretStr | None = None
    openai_vision_model: str = "gpt-4o-mini"

    # Matching / scoring
    fuzzy_confidence_threshold: float = 90.0
    min_opportunity_score: float = 75.0
    scan_interval_seconds: int = 300
    scan_queries: str = (
        "pokemon card,pokemon tcg,pokemon holo,pokemon rare,"
        "pokemon collection,old pokemon card,pokimon card,poke mon card"
    )

    # Database — PostgreSQL on Railway; SQLite OK for local MVP demos
    database_url: str = "sqlite:///./data/pokebargain.db"

    # Dashboard
    host: str = "0.0.0.0"
    port: int = 8000
    auto_scan: bool = True

    @property
    def search_terms(self) -> list[str]:
        return [q.strip() for q in self.scan_queries.split(",") if q.strip()]


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
