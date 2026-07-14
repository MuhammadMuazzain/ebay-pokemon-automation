"""Single-card vs bulk / sealed / accessory filters."""

from __future__ import annotations

import re
from dataclasses import dataclass

_REJECT_PATTERNS = [
    (re.compile(r"\b(lot|bulk|bundle|x\d{2,}|\d{2,}\s*cards?)\b", re.I), "bulk_lot"),
    (re.compile(r"\b(booster|etb|elite trainer|sealed|display|box case)\b", re.I), "sealed"),
    (
        re.compile(
            r"\b(sleeve|binder|deck box|toploader|top loader|penny sleeve|playmat|"
            r"dice|coin|pin|plush|figure|sticker)\b",
            re.I,
        ),
        "accessory",
    ),
]


@dataclass(frozen=True)
class ListingFilterResult:
    is_single_card: bool
    reason: str | None


def is_likely_single_card(title: str) -> ListingFilterResult:
    for pattern, reason in _REJECT_PATTERNS:
        if pattern.search(title):
            return ListingFilterResult(False, reason)
    return ListingFilterResult(True, None)
