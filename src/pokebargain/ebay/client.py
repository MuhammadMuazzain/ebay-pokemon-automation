"""Thin httpx wrapper for eBay REST with retry/backoff."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any

import httpx

from pokebargain.ebay.errors import TRANSIENT_STATUSES, EbayApiError
from pokebargain.logging import get_logger

log = get_logger(__name__)

TokenProvider = Callable[[], str]


class EbayClient:
    def __init__(
        self,
        api_host: str,
        token_provider: TokenProvider,
        *,
        http: httpx.Client | None = None,
        max_retries: int = 4,
    ) -> None:
        self.api_base = f"https://{api_host}"
        self._token_provider = token_provider
        self._http = http or httpx.Client(timeout=30.0)
        self.max_retries = max_retries

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
    ) -> httpx.Response:
        final_headers = {"Authorization": f"Bearer {self._token_provider()}"}
        if headers:
            final_headers.update(headers)

        last: httpx.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._http.request(
                    method, url, headers=final_headers, params=params, data=data
                )
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise EbayApiError(0, message=f"network error: {exc}") from exc
                time.sleep(0.5 * (2**attempt) + random.uniform(0, 0.25))
                continue

            if response.status_code in expected:
                return response

            last = response
            if response.status_code in TRANSIENT_STATUSES and attempt < self.max_retries:
                log.warning(
                    "eBay %s %s -> %d; retry %d",
                    method,
                    url,
                    response.status_code,
                    attempt + 1,
                )
                time.sleep(0.5 * (2**attempt))
                continue
            break

        assert last is not None
        raise EbayApiError(last.status_code, errors=_extract_errors(last))

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)


def _extract_errors(response: httpx.Response) -> list[dict[str, Any]]:
    try:
        body = response.json()
    except ValueError:
        return [{"message": response.text[:500]}]
    errors = body.get("errors") if isinstance(body, dict) else None
    return errors if isinstance(errors, list) else [{"message": str(body)[:500]}]
