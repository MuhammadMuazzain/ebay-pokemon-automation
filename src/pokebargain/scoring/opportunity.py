"""Hidden Opportunity Score — primary bargain-detection feature."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class OpportunityResult:
    score: float
    discount_amount: Decimal | None
    discount_pct: float | None
    potential_profit: Decimal | None
    breakdown: dict[str, Any]


def compute_opportunity_score(
    *,
    listing_price: Decimal,
    market_value: Decimal | None,
    match_confidence: float,
    title_quality: str,
    has_card_number: bool,
    misspelled_name: bool,
    misspelled_set: bool,
    match_method: str,
    vision_better_than_title: bool = False,
) -> OpportunityResult:
    """Score how likely a listing is an overlooked / undervalued bargain (0–100).

    Factors drawn from the product brief:
    - Misspelled Pokémon / set names
    - Poor, vague, or generic titles
    - Missing card number
    - Vision identifies a better card than the title suggests
    - Gap between asking price and market value
    - Identification confidence
    """
    breakdown: dict[str, Any] = {}
    score = 0.0

    discount_amount: Decimal | None = None
    discount_pct: float | None = None
    potential_profit: Decimal | None = None

    if market_value and market_value > 0:
        discount_amount = market_value - listing_price
        discount_pct = float((discount_amount / market_value) * 100)
        # Assume ~10% fees/shipping friction for potential profit estimate
        potential_profit = discount_amount * Decimal("0.9")
        if discount_pct >= 40:
            price_pts = 35.0
        elif discount_pct >= 25:
            price_pts = 28.0
        elif discount_pct >= 15:
            price_pts = 20.0
        elif discount_pct >= 5:
            price_pts = 10.0
        else:
            price_pts = 0.0
        if discount_pct < 0:
            price_pts = 0.0
        breakdown["price_gap"] = round(price_pts, 1)
        score += price_pts
    else:
        breakdown["price_gap"] = 0.0

    # Title / discoverability signals (why other buyers miss it)
    title_pts = 0.0
    if misspelled_name:
        title_pts += 15.0
    if misspelled_set:
        title_pts += 10.0
    if title_quality == "generic":
        title_pts += 12.0
    elif title_quality == "vague":
        title_pts += 8.0
    elif title_quality == "misspelled":
        title_pts += 10.0
    if not has_card_number:
        title_pts += 6.0
    title_pts = min(title_pts, 35.0)
    breakdown["title_signals"] = round(title_pts, 1)
    score += title_pts

    # Match confidence
    if match_confidence >= 95:
        conf_pts = 15.0
    elif match_confidence >= 85:
        conf_pts = 12.0
    elif match_confidence >= 70:
        conf_pts = 8.0
    else:
        conf_pts = 3.0
    breakdown["confidence"] = conf_pts
    score += conf_pts

    # Vision upgrade vs title
    vision_pts = 0.0
    if match_method == "vision":
        vision_pts += 5.0
    if vision_better_than_title:
        vision_pts += 10.0
    breakdown["vision"] = vision_pts
    score += vision_pts

    score = max(0.0, min(100.0, round(score, 1)))
    breakdown["total"] = score
    return OpportunityResult(
        score=score,
        discount_amount=discount_amount,
        discount_pct=discount_pct,
        potential_profit=potential_profit,
        breakdown=breakdown,
    )
