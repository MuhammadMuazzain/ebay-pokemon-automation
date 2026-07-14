"""eBay OAuth2 application (client-credentials) tokens for the Browse API."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import httpx

from pokebargain.config import ConfigError, Settings
from pokebargain.ebay.errors import EbayAuthError
from pokebargain.logging import get_logger

log = get_logger(__name__)

APP_SCOPE = "https://api.ebay.com/oauth/api_scope"
_EXPIRY_SKEW = timedelta(seconds=60)


class AppTokenProvider:
    """Mints and caches application tokens for buy.browse / Browse API search."""

    def __init__(self, settings: Settings, http: httpx.Client | None = None) -> None:
        if not settings.ebay_client_id or not settings.ebay_client_secret:
            raise ConfigError(
                "POKEBARGAIN_EBAY_CLIENT_ID and POKEBARGAIN_EBAY_CLIENT_SECRET are required"
            )
        self._client_id = settings.ebay_client_id.get_secret_value()
        self._client_secret = settings.ebay_client_secret.get_secret_value()
        self._api_host = settings.ebay_api_host
        self._http = http or httpx.Client(timeout=30.0)
        self._access_token: str | None = None
        self._expires_at: datetime | None = None

    def __call__(self) -> str:
        now = datetime.now(UTC)
        if self._access_token and self._expires_at and now < self._expires_at - _EXPIRY_SKEW:
            return self._access_token
        return self._mint()

    def _mint(self) -> str:
        basic = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        url = f"https://{self._api_host}/identity/v1/oauth2/token"
        response = self._http.post(
            url,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": APP_SCOPE},
        )
        if response.status_code != 200:
            raise EbayAuthError(f"failed to mint app token: {response.status_code} {response.text}")
        body = response.json()
        self._access_token = body["access_token"]
        self._expires_at = datetime.now(UTC) + timedelta(seconds=int(body["expires_in"]))
        log.info("Minted eBay application token (expires in %ss)", body["expires_in"])
        return self._access_token
