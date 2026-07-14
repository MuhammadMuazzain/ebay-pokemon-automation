"""eBay API errors."""

from __future__ import annotations

from typing import Any

TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class EbayError(RuntimeError):
    pass


class EbayAuthError(EbayError):
    pass


class EbayApiError(EbayError):
    def __init__(
        self,
        status_code: int,
        *,
        message: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.errors = errors or []
        detail = message or (str(self.errors) if self.errors else "unknown error")
        super().__init__(f"eBay API {status_code}: {detail}")
