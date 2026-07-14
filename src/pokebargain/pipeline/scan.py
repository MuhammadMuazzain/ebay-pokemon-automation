"""Scan pipeline: discover → filter → fuzzy match → (optional) vision → price → score."""

from __future__ import annotations

from decimal import Decimal

from pokebargain.config import Settings
from pokebargain.db.base import Database
from pokebargain.db.models import Listing
from pokebargain.db.repository import ListingRepository, ScanRepository
from pokebargain.ebay.browse import EbayListingSummary, search_listings
from pokebargain.ebay.client import EbayClient
from pokebargain.logging import get_logger
from pokebargain.matching.filter import is_likely_single_card
from pokebargain.matching.fuzzy import FuzzyMatchResult, match_listing_to_card
from pokebargain.scoring.opportunity import compute_opportunity_score
from pokebargain.tcg.client import PokemonTcgClient, TcgCard
from pokebargain.vision.openai_client import OpenAIVisionIdentifier

log = get_logger(__name__)


class ScanPipeline:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        ebay: EbayClient,
        tcg: PokemonTcgClient,
        vision: OpenAIVisionIdentifier | None = None,
    ) -> None:
        self.settings = settings
        self.db = database
        self.ebay = ebay
        self.tcg = tcg
        self.vision = vision
        self._catalogue: list[TcgCard] | None = None

    def _catalogue_cards(self) -> list[TcgCard]:
        if self._catalogue is None:
            self._catalogue = self.tcg.load_name_index()
        return self._catalogue

    def run(self, *, limit_per_query: int = 40) -> dict[str, int]:
        with self.db.session() as session:
            scans = ScanRepository(session)
            listings = ListingRepository(session)
            run = scans.start()

            fetched = new = scored = vision_calls = 0
            try:
                catalogue = self._catalogue_cards()
                for term in self.settings.search_terms:
                    log.info("Scanning eBay UK for %r", term)
                    summaries = search_listings(
                        self.ebay,
                        term,
                        self.settings.ebay_marketplace_id,
                        limit=limit_per_query,
                    )
                    fetched += len(summaries)
                    for summary in summaries:
                        if listings.exists(summary.item_id):
                            continue
                        created = self._analyse(listings, summary, term, catalogue)
                        if created is None:
                            continue
                        new += 1
                        if created.match_method == "vision":
                            vision_calls += 1
                        if created.opportunity_score is not None:
                            scored += 1

                scans.finish(
                    run,
                    listings_fetched=fetched,
                    listings_new=new,
                    listings_scored=scored,
                    vision_calls=vision_calls,
                )
            except Exception as exc:
                log.exception("Scan failed")
                scans.finish(run, status="failed", error=str(exc))
                raise

            return {
                "fetched": fetched,
                "new": new,
                "scored": scored,
                "vision_calls": vision_calls,
            }

    def _analyse(
        self,
        repo: ListingRepository,
        summary: EbayListingSummary,
        search_term: str,
        catalogue: list[TcgCard],
    ) -> Listing | None:
        filt = is_likely_single_card(summary.title)
        listing = Listing(
            ebay_item_id=summary.item_id,
            title=summary.title,
            price=summary.price,
            currency=summary.currency,
            image_url=summary.image_url,
            listing_url=summary.listing_url,
            condition=summary.condition,
            is_single_card=filt.is_single_card,
            filter_reason=filt.reason,
            search_term=search_term,
        )
        if not filt.is_single_card:
            repo.add(listing)
            return listing

        fuzzy = match_listing_to_card(summary.title, catalogue)
        card = fuzzy.card
        match_method = "fuzzy"
        confidence = fuzzy.confidence
        vision_better = False
        estimated_condition = None
        language = "English"

        if (
            confidence < self.settings.fuzzy_confidence_threshold
            and self.vision is not None
            and summary.image_url
        ):
            vision_result = self.vision.identify(summary.image_url, summary.title)
            vision_calls_card = self._resolve_vision_card(vision_result, catalogue)
            if vision_calls_card is not None:
                # Prefer vision when it finds a card and fuzzy was weak
                if card is None or vision_result.confidence >= confidence:
                    vision_better = card is None or (
                        vision_calls_card.name.lower() != (card.name.lower() if card else "")
                    )
                    card = vision_calls_card
                    confidence = max(confidence, vision_result.confidence)
                    match_method = "vision"
                    estimated_condition = vision_result.estimated_condition
                    language = vision_result.language or language

        listing.match_method = match_method
        listing.match_confidence = confidence
        listing.title_quality = fuzzy.title_quality

        if card is not None:
            listing.card_name = card.name
            listing.set_name = card.set_name
            listing.card_number = card.number
            listing.rarity = card.rarity
            listing.tcg_card_id = card.id
            listing.card_image_url = card.image_large or card.image_small
            listing.language = language
            listing.estimated_condition = estimated_condition
            market = card.market_price_gbp
            listing.market_value = market

            opportunity = compute_opportunity_score(
                listing_price=summary.price,
                market_value=market,
                match_confidence=confidence,
                title_quality=fuzzy.title_quality,
                has_card_number=fuzzy.has_card_number,
                misspelled_name=fuzzy.likely_misspelled_name,
                misspelled_set=fuzzy.likely_misspelled_set,
                match_method=match_method,
                vision_better_than_title=vision_better,
            )
            listing.opportunity_score = opportunity.score
            listing.discount_amount = opportunity.discount_amount
            listing.discount_pct = opportunity.discount_pct
            listing.potential_profit = opportunity.potential_profit
            listing.score_breakdown = opportunity.breakdown
        else:
            # Still score title-quality signals even without a market match
            opportunity = compute_opportunity_score(
                listing_price=summary.price,
                market_value=None,
                match_confidence=confidence,
                title_quality=fuzzy.title_quality,
                has_card_number=fuzzy.has_card_number,
                misspelled_name=fuzzy.likely_misspelled_name,
                misspelled_set=fuzzy.likely_misspelled_set,
                match_method=match_method,
            )
            listing.opportunity_score = opportunity.score
            listing.score_breakdown = opportunity.breakdown

        repo.add(listing)
        return listing

    def _resolve_vision_card(
        self,
        vision_result: object,
        catalogue: list[TcgCard],
    ) -> TcgCard | None:
        from pokebargain.vision.openai_client import VisionIdentification

        assert isinstance(vision_result, VisionIdentification)
        if not vision_result.card_name:
            return None
        # Prefer live API lookup, fall back to fuzzy against catalogue
        hits = self.tcg.find_by_name(vision_result.card_name, set_hint=vision_result.set_name)
        if hits:
            if vision_result.card_number:
                for hit in hits:
                    if hit.number == vision_result.card_number:
                        return hit
            return hits[0]
        fuzzy: FuzzyMatchResult = match_listing_to_card(
            f"{vision_result.card_name} {vision_result.set_name or ''} "
            f"{vision_result.card_number or ''}",
            catalogue,
        )
        return fuzzy.card


def seed_demo_listings(database: Database) -> int:
    """Insert illustrative bargain opportunities so the dashboard demos without API keys."""
    demos = [
        {
            "ebay_item_id": "demo-001",
            "title": "Charzard holo pokemon card",
            "price": Decimal("45.00"),
            "card_name": "Charizard",
            "set_name": "Base Set",
            "card_number": "4",
            "market_value": Decimal("180.00"),
            "opportunity_score": 94.0,
            "discount_pct": 75.0,
            "potential_profit": Decimal("121.50"),
            "match_method": "vision",
            "match_confidence": 92.0,
            "title_quality": "misspelled",
            "image_url": "https://images.pokemontcg.io/base1/4_hires.png",
            "card_image_url": "https://images.pokemontcg.io/base1/4_hires.png",
            "listing_url": "https://www.ebay.co.uk/",
        },
        {
            "ebay_item_id": "demo-002",
            "title": "pokemon rare card",
            "price": Decimal("12.99"),
            "card_name": "Pikachu",
            "set_name": "Surfing Pikachu",
            "card_number": "25",
            "market_value": Decimal("35.00"),
            "opportunity_score": 82.0,
            "discount_pct": 62.9,
            "potential_profit": Decimal("19.81"),
            "match_method": "vision",
            "match_confidence": 88.0,
            "title_quality": "generic",
            "image_url": "https://images.pokemontcg.io/basep/25_hires.png",
            "card_image_url": "https://images.pokemontcg.io/basep/25_hires.png",
            "listing_url": "https://www.ebay.co.uk/",
        },
        {
            "ebay_item_id": "demo-003",
            "title": "Obsidan Flames Booster Art Rare",
            "price": Decimal("8.50"),
            "card_name": "Charizard ex",
            "set_name": "Obsidian Flames",
            "card_number": "223",
            "market_value": Decimal("28.00"),
            "opportunity_score": 88.0,
            "discount_pct": 69.6,
            "potential_profit": Decimal("17.55"),
            "match_method": "fuzzy",
            "match_confidence": 86.0,
            "title_quality": "misspelled",
            "image_url": "https://images.pokemontcg.io/sv3/223_hires.png",
            "card_image_url": "https://images.pokemontcg.io/sv3/223_hires.png",
            "listing_url": "https://www.ebay.co.uk/",
        },
    ]
    added = 0
    with database.session() as session:
        repo = ListingRepository(session)
        for row in demos:
            if repo.exists(row["ebay_item_id"]):  # type: ignore[arg-type]
                continue
            market = row["market_value"]
            price = row["price"]
            assert isinstance(market, Decimal) and isinstance(price, Decimal)
            listing = Listing(
                ebay_item_id=str(row["ebay_item_id"]),
                title=str(row["title"]),
                price=price,
                currency="GBP",
                image_url=str(row.get("image_url")),
                listing_url=str(row.get("listing_url")),
                is_single_card=True,
                card_name=str(row["card_name"]),
                set_name=str(row["set_name"]),
                card_number=str(row["card_number"]),
                card_image_url=str(row.get("card_image_url")),
                match_method=str(row["match_method"]),
                match_confidence=float(row["match_confidence"]),  # type: ignore[arg-type]
                title_quality=str(row["title_quality"]),
                market_value=market,
                discount_amount=market - price,
                discount_pct=float(row["discount_pct"]),  # type: ignore[arg-type]
                potential_profit=row["potential_profit"],  # type: ignore[arg-type]
                opportunity_score=float(row["opportunity_score"]),  # type: ignore[arg-type]
                score_breakdown={"demo": True},
                language="English",
            )
            repo.add(listing)
            added += 1
    return added
