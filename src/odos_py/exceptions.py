"""Exception hierarchy for the Odos client.

All errors raised by this library derive from :class:`OdosError`, so callers
can catch that one base class to handle any failure originating here::

    try:
        client.quote(request)
    except OdosRateLimitError as exc:
        ...  # back off and retry later
    except OdosAPIError as exc:
        ...  # inspect exc.status_code / exc.body
    except OdosError:
        ...  # any other library error
"""

from __future__ import annotations

from typing import Any, Optional


class OdosError(Exception):
    """Base class for all errors raised by this library.

    Catch this to handle any failure originating from ``odos_py`` without
    distinguishing the specific subtype.
    """


class OdosAPIError(OdosError):
    """Raised when the Odos API returns a non-success HTTP status.

    Also raised for client-side protocol problems, such as a quote response
    that lacks a ``path_id`` during :meth:`~odos_py.OdosClient.swap`.

    Attributes:
        status_code: The HTTP status code returned by the API, or ``None`` when
            the error did not originate from an HTTP response.
        body: The parsed response body (JSON when decodable, otherwise the raw
            text), or ``None``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Any = None,
    ) -> None:
        """Initialize the error.

        Args:
            message: Human-readable description of the failure.
            status_code: HTTP status code associated with the failure, if any.
            body: Parsed response body associated with the failure, if any.
        """
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class OdosRateLimitError(OdosAPIError):
    """Raised on HTTP 429 after the client's retries are exhausted.

    The client automatically retries 429 responses with exponential backoff
    (honouring ``Retry-After``); this is raised only once ``max_retries`` is
    reached.

    Attributes:
        retry_after: The server-advised wait in seconds parsed from the
            ``Retry-After`` header, or ``None`` when absent or unparseable.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Any = None,
        retry_after: Optional[float] = None,
    ) -> None:
        """Initialize the rate-limit error.

        Args:
            message: Human-readable description of the failure.
            status_code: HTTP status code (typically ``429``).
            body: Parsed response body associated with the failure, if any.
            retry_after: Server-advised wait in seconds, if provided.
        """
        super().__init__(message, status_code=status_code, body=body)
        self.retry_after = retry_after
