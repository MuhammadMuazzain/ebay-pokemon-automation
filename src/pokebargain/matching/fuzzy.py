"""Fuzzy title matching against the Pokémon TCG card database (RapidFuzz)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from pokebargain.tcg.client import TcgCard

# Common listing noise that hurts match quality.
_NOISE = re.compile(
    r"\b(pokemon|pokémon|tcg|card|holo|rare|nm|mint|lp|mp|hp|dmg|"
    r"english|eng|psa|cgc|bgs|graded|shipping|free)\b",
    re.IGNORECASE,
)

_SET_ALIASES: dict[str, str] = {
    "obsidan flames": "obsidian flames",
    "obsidan": "obsidian flames",
    "paldea evolving": "paldea evolved",
    "evolving sky": "evolving skies",
    "brilliant star": "brilliant stars",
    "base": "base set",
}


@dataclass(frozen=True)
class FuzzyMatchResult:
    card: TcgCard | None
    confidence: float
    corrected_title: str
    title_quality: str  # clean | misspelled | vague | generic
    has_card_number: bool
    likely_misspelled_name: bool
    likely_misspelled_set: bool


def classify_title_quality(title: str) -> str:
    lowered = title.lower().strip()
    tokens = [t for t in re.split(r"\W+", lowered) if t]
    if len(tokens) <= 3 or lowered in {"pokemon card", "pokemon tcg", "pokemon holo"}:
        return "generic"
    if not re.search(r"\d+(/\d+)?", title):
        # No number and short descriptive content
        if len(tokens) <= 5:
            return "vague"
    return "clean"


def _normalise(text: str) -> str:
    text = text.lower()
    for wrong, right in _SET_ALIASES.items():
        text = text.replace(wrong, right)
    text = _NOISE.sub(" ", text)
    text = re.sub(r"[^a-z0-9/\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has_card_number(title: str) -> bool:
    return bool(re.search(r"\b\d{1,3}\s*/\s*\d{1,3}\b", title) or re.search(r"#\s*\d+", title))


def match_listing_to_card(
    title: str,
    catalogue: list[TcgCard],
    *,
    score_cutoff: float = 55.0,
) -> FuzzyMatchResult:
    """Correct spelling mistakes and match vague/incomplete titles to the TCG DB."""
    quality = classify_title_quality(title)
    has_number = _has_card_number(title)
    normalised = _normalise(title)
    if not catalogue or not normalised:
        return FuzzyMatchResult(
            card=None,
            confidence=0.0,
            corrected_title=normalised,
            title_quality=quality,
            has_card_number=has_number,
            likely_misspelled_name=False,
            likely_misspelled_set=False,
        )

    # Candidate strings: "Name | Set | Number"
    choices: dict[str, TcgCard] = {}
    for card in catalogue:
        label = f"{card.name} {card.set_name} {card.number}".strip()
        choices[label] = card
        choices[card.name.lower()] = card

    result = process.extractOne(
        normalised,
        list(choices.keys()),
        scorer=fuzz.token_set_ratio,
        score_cutoff=score_cutoff,
    )
    if result is None:
        return FuzzyMatchResult(
            card=None,
            confidence=0.0,
            corrected_title=normalised,
            title_quality="misspelled" if quality == "clean" else quality,
            has_card_number=has_number,
            likely_misspelled_name=True,
            likely_misspelled_set=False,
        )

    label, score, _ = result
    card = choices[label]
    # Detect misspellings: raw title token-set ratio vs corrected name is lower
    raw_vs_name = fuzz.token_set_ratio(title.lower(), card.name.lower())
    misspelled_name = raw_vs_name < 85 and score >= 70
    misspelled_set = (
        bool(card.set_name)
        and fuzz.partial_ratio(title.lower(), card.set_name.lower()) < 70
        and fuzz.partial_ratio(normalised, card.set_name.lower()) >= 70
    )
    if misspelled_name or misspelled_set:
        quality = "misspelled"

    corrected = f"{card.name} {card.set_name} {card.number}".strip()
    return FuzzyMatchResult(
        card=card,
        confidence=float(score),
        corrected_title=corrected,
        title_quality=quality,
        has_card_number=has_number,
        likely_misspelled_name=misspelled_name,
        likely_misspelled_set=misspelled_set,
    )
