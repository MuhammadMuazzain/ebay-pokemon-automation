"""Unit tests for fuzzy matching and single-card filters."""

from __future__ import annotations

from decimal import Decimal

from pokebargain.matching.filter import is_likely_single_card
from pokebargain.matching.fuzzy import classify_title_quality, match_listing_to_card
from pokebargain.scoring.opportunity import compute_opportunity_score
from pokebargain.tcg.client import TcgCard


def _card(name: str, set_name: str = "Base Set", number: str = "4") -> TcgCard:
    return TcgCard(
        id="base1-4",
        name=name,
        set_name=set_name,
        set_id="base1",
        number=number,
        rarity="Rare Holo",
        image_small=None,
        image_large=None,
        market_price_gbp=Decimal("100"),
        market_price_usd=Decimal("120"),
    )


def test_rejects_bulk_and_sealed() -> None:
    assert is_likely_single_card("Pokemon card lot of 50").is_single_card is False
    assert is_likely_single_card("Sealed ETB booster box").is_single_card is False
    assert is_likely_single_card("Charizard Base Set 4/102").is_single_card is True


def test_fuzzy_corrects_charzard() -> None:
    catalogue = [_card("Charizard"), _card("Pikachu", "Base Set", "58")]
    result = match_listing_to_card("Charzard holo pokemon card", catalogue)
    assert result.card is not None
    assert result.card.name == "Charizard"
    assert result.confidence > 60
    assert result.likely_misspelled_name or result.title_quality == "misspelled"


def test_obsidian_alias() -> None:
    catalogue = [_card("Charizard ex", "Obsidian Flames", "223")]
    result = match_listing_to_card("Obsidan Flames Charizard", catalogue)
    assert result.card is not None
    assert "Obsidian" in result.card.set_name or result.confidence > 50


def test_generic_title_quality() -> None:
    assert classify_title_quality("pokemon card") == "generic"


def test_opportunity_score_rewards_misspell_and_discount() -> None:
    result = compute_opportunity_score(
        listing_price=Decimal("40"),
        market_value=Decimal("100"),
        match_confidence=92,
        title_quality="misspelled",
        has_card_number=False,
        misspelled_name=True,
        misspelled_set=True,
        match_method="vision",
        vision_better_than_title=True,
    )
    assert result.score >= 75
    assert result.discount_pct is not None and result.discount_pct == 60.0
    assert result.potential_profit is not None
