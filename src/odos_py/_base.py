"""Shared configuration and HTTP plumbing for the sync and async clients."""

from __future__ import annotations

from typing import Any, Mapping, Optional

import httpx

DEFAULT_BASE_URL = "https://api.odos.xyz"
DEFAULT_API_KEY_HEADER = "x-api-key"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.5
DEFAULT_TIMEOUT = 30.0


class OdosConfig:
    """Holds connection settings shared by both client flavours."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        api_key_header: str = DEFAULT_API_KEY_HEADER,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_key_header = api_key_header
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout

    def headers(self) -> dict[str, str]:
        """Build default request headers, including the API key when set."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers[self.api_key_header] = self.api_key
        return headers

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"


def parse_retry_after(headers: Mapping[str, str]) -> Optional[float]:
    """Extract a numeric ``Retry-After`` (seconds) header if present."""
    value = headers.get("Retry-After") or headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def backoff_delay(base: float, attempt: int, retry_after: Optional[float]) -> float:
    """Compute the wait before the next retry (exponential, server-hint aware).

    ``attempt`` is zero-based. A server-provided ``Retry-After`` wins when it is
    larger than the computed exponential backoff.
    """
    computed = base * float(2**attempt)
    if retry_after is not None:
        return max(computed, retry_after)
    return computed


def safe_json(response: httpx.Response) -> Any:
    """Return parsed JSON, or the raw text if the body is not valid JSON."""
    try:
        return response.json()
    except ValueError:
        return response.text
