"""eBay Browse API — broad Pokémon listing discovery on eBay UK."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from pokebargain.ebay.client import EbayClient

_BROWSE_PATH = "/buy/browse/v1/item_summary/search"

# Prefer Buy It Now singles; exclude auctions by default for MVP.
_DEFAULT_FILTER = "buyingOptions:{FIXED_PRICE},conditions:{NEW|LIKE_NEW|VERY_GOOD|GOOD|ACCEPTABLE}"


@dataclass(frozen=True)
class EbayListingSummary:
    item_id: str
    title: str
    price: Decimal
    currency: str
    image_url: str | None
    listing_url: str | None
    condition: str | None


def search_listings(
    client: EbayClient,
    query: str,
    marketplace_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[EbayListingSummary]:
    """Broad search for Pokémon-related Buy It Now listings."""
    params: dict[str, Any] = {
        "q": query,
        "limit": str(limit),
        "offset": str(offset),
        "filter": _DEFAULT_FILTER,
    }
    body = client.get(
        f"{client.api_base}{_BROWSE_PATH}",
        params=params,
        headers={"X-EBAY-C-MARKETPLACE-ID": marketplace_id},
    ).json()

    results: list[EbayListingSummary] = []
    for summary in body.get("itemSummaries", []):
        priced = _price(summary.get("price"))
        if priced is None:
            continue
        value, currency = priced
        item_id = str(summary.get("itemId") or summary.get("legacyItemId") or "")
        if not item_id:
            continue
        image = summary.get("image") or {}
        results.append(
            EbayListingSummary(
                item_id=item_id,
                title=summary.get("title") or "",
                price=value,
                currency=currency,
                image_url=image.get("imageUrl"),
                listing_url=summary.get("itemWebUrl"),
                condition=summary.get("condition"),
            )
        )
    return results


def _price(node: dict[str, Any] | None) -> tuple[Decimal, str] | None:
    if not node:
        return None
    try:
        return Decimal(str(node["value"])), node.get("currency", "GBP")
    except (KeyError, InvalidOperation, TypeError):
        return None
