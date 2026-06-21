"""Tests for the exception hierarchy."""

from __future__ import annotations

from odos_py.exceptions import (
    OdosAPIError,
    OdosError,
    OdosRateLimitError,
)


def test_rate_limit_is_an_api_error() -> None:
    assert issubclass(OdosRateLimitError, OdosAPIError)
    assert issubclass(OdosAPIError, OdosError)


def test_api_error_carries_status_and_body() -> None:
    err = OdosAPIError("boom", status_code=400, body={"detail": "bad"})
    assert err.status_code == 400
    assert err.body == {"detail": "bad"}
    assert "boom" in str(err)


def test_rate_limit_error_exposes_retry_after() -> None:
    err = OdosRateLimitError("slow down", status_code=429, retry_after=2.5)
    assert err.status_code == 429
    assert err.retry_after == 2.5
