"""Exception hierarchy for the Odos client."""

from __future__ import annotations

from typing import Any, Optional


class OdosError(Exception):
    """Base class for all errors raised by this library."""


class OdosAPIError(OdosError):
    """Raised when the Odos API returns a non-success HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class OdosRateLimitError(OdosAPIError):
    """Raised on HTTP 429 after retries are exhausted.

    ``retry_after`` is the server-advised wait in seconds, when available.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Any = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.retry_after = retry_after
