"""OpenAI Vision identification — used only when fuzzy confidence is below threshold."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from openai import OpenAI

from pokebargain.config import ConfigError, Settings
from pokebargain.logging import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You identify Pokémon TCG cards from listing photos.
Return ONLY valid JSON with keys:
card_name, set_name, card_number, language, estimated_condition, confidence (0-100).
If unsure, still guess but lower confidence. Prefer English set names."""


@dataclass(frozen=True)
class VisionIdentification:
    card_name: str | None
    set_name: str | None
    card_number: str | None
    language: str | None
    estimated_condition: str | None
    confidence: float
    raw: dict[str, Any]


class OpenAIVisionIdentifier:
    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        if not settings.openai_api_key:
            raise ConfigError("POKEBARGAIN_OPENAI_API_KEY is required for vision identification")
        self._model = settings.openai_vision_model
        self._client = client or OpenAI(api_key=settings.openai_api_key.get_secret_value())

    def identify(self, image_url: str, listing_title: str) -> VisionIdentification:
        log.info("Calling OpenAI Vision for ambiguous listing: %s", listing_title[:80])
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Listing title (may be wrong/misspelled): {listing_title}\n"
                                "Identify the card in the image."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            max_tokens=300,
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        data = _parse_json(content)
        return VisionIdentification(
            card_name=data.get("card_name"),
            set_name=data.get("set_name"),
            card_number=data.get("card_number") and str(data.get("card_number")),
            language=data.get("language"),
            estimated_condition=data.get("estimated_condition"),
            confidence=float(data.get("confidence") or 0),
            raw=data,
        )


def _parse_json(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        # Fallback: try to find a JSON object
        start, end = content.find("{"), content.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


def download_ok(url: str, http: httpx.Client | None = None) -> bool:
    client = http or httpx.Client(timeout=10.0)
    try:
        return client.head(url, follow_redirects=True).status_code < 400
    except httpx.HTTPError:
        return False
