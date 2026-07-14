"""Pokémon TCG API client — card database + market prices (TCGplayer / Cardmarket)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from pokebargain.config import Settings
from pokebargain.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class TcgCard:
    id: str
    name: str
    set_name: str
    set_id: str
    number: str
    rarity: str | None
    image_small: str | None
    image_large: str | None
    market_price_gbp: Decimal | None
    market_price_usd: Decimal | None


class PokemonTcgClient:
    def __init__(self, settings: Settings, http: httpx.Client | None = None) -> None:
        self._base = settings.pokemon_tcg_base_url.rstrip("/")
        self._api_key = (
            settings.pokemon_tcg_api_key.get_secret_value()
            if settings.pokemon_tcg_api_key
            else None
        )
        self._http = http or httpx.Client(timeout=30.0)
        self._card_cache: list[TcgCard] | None = None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        return headers

    def search_cards(self, query: str, *, page_size: int = 20) -> list[TcgCard]:
        """Search cards with the Pokémon TCG API query language."""
        response = self._http.get(
            f"{self._base}/cards",
            params={"q": query, "pageSize": str(page_size)},
            headers=self._headers(),
        )
        response.raise_for_status()
        return [_parse_card(item) for item in response.json().get("data", [])]

    def find_by_name(self, name: str, *, set_hint: str | None = None) -> list[TcgCard]:
        parts = [f'name:"{name}"']
        if set_hint:
            parts.append(f'set.name:"{set_hint}"')
        return self.search_cards(" ".join(parts))

    def get_card(self, card_id: str) -> TcgCard | None:
        response = self._http.get(f"{self._base}/cards/{card_id}", headers=self._headers())
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json().get("data")
        return _parse_card(data) if data else None

    def load_name_index(self, *, page_size: int = 250, max_pages: int = 8) -> list[TcgCard]:
        """Load a working subset of English cards for fuzzy title matching.

        Full catalogue download is expensive; for MVP we page the first N results
        ordered by relevance and cache in-memory for the process lifetime.
        """
        if self._card_cache is not None:
            return self._card_cache

        cards: list[TcgCard] = []
        for page in range(1, max_pages + 1):
            response = self._http.get(
                f"{self._base}/cards",
                params={
                    "q": "supertype:Pokémon",
                    "page": str(page),
                    "pageSize": str(page_size),
                    "select": "id,name,number,rarity,set,images,tcgplayer,cardmarket",
                },
                headers=self._headers(),
            )
            response.raise_for_status()
            batch = [_parse_card(item) for item in response.json().get("data", [])]
            if not batch:
                break
            cards.extend(batch)
            log.info("Loaded Pokémon TCG index page %d (%d cards)", page, len(cards))
        self._card_cache = cards
        return cards


def _parse_card(data: dict[str, Any]) -> TcgCard:
    images = data.get("images") or {}
    set_info = data.get("set") or {}
    usd = _tcgplayer_market(data.get("tcgplayer"))
    eur = _cardmarket_trend(data.get("cardmarket"))
    # Approximate EUR→GBP for UK dashboard until FX feed is added.
    gbp = (eur * Decimal("0.86")) if eur is not None else None
    if gbp is None and usd is not None:
        gbp = usd * Decimal("0.79")
    return TcgCard(
        id=data["id"],
        name=data.get("name") or "",
        set_name=set_info.get("name") or "",
        set_id=set_info.get("id") or "",
        number=str(data.get("number") or ""),
        rarity=data.get("rarity"),
        image_small=images.get("small"),
        image_large=images.get("large"),
        market_price_gbp=gbp,
        market_price_usd=usd,
    )


def _tcgplayer_market(node: dict[str, Any] | None) -> Decimal | None:
    if not node:
        return None
    prices = node.get("prices") or {}
    for variant in ("holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"):
        entry = prices.get(variant) or {}
        market = entry.get("market") or entry.get("mid")
        if market is not None:
            return Decimal(str(market))
    return None


def _cardmarket_trend(node: dict[str, Any] | None) -> Decimal | None:
    if not node:
        return None
    prices = node.get("prices") or {}
    for key in ("trendPrice", "averageSellPrice", "lowPrice"):
        if prices.get(key) is not None:
            return Decimal(str(prices[key]))
    return None
