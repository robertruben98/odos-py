"""Unit tests for the pure helpers in odos_py._base."""

from __future__ import annotations

from odos_py._base import OdosConfig, backoff_delay, parse_retry_after


def test_backoff_is_exponential() -> None:
    assert backoff_delay(0.5, 0, None) == 0.5
    assert backoff_delay(0.5, 1, None) == 1.0
    assert backoff_delay(0.5, 2, None) == 2.0


def test_backoff_honors_larger_retry_after() -> None:
    # Server hint of 10s beats the computed 0.5s.
    assert backoff_delay(0.5, 0, 10.0) == 10.0
    # Computed beats a smaller hint.
    assert backoff_delay(0.5, 3, 1.0) == 4.0


def test_parse_retry_after_numeric() -> None:
    assert parse_retry_after({"Retry-After": "3"}) == 3.0
    assert parse_retry_after({"retry-after": "2.5"}) == 2.5


def test_parse_retry_after_missing_or_invalid() -> None:
    assert parse_retry_after({}) is None
    assert parse_retry_after({"Retry-After": "Wed, 21 Oct 2015"}) is None


def test_config_strips_trailing_slash_and_builds_url() -> None:
    cfg = OdosConfig(base_url="https://x.test/")
    assert cfg.base_url == "https://x.test"
    assert cfg.url("/sor/quote/v2") == "https://x.test/sor/quote/v2"
    assert cfg.url("sor/quote/v2") == "https://x.test/sor/quote/v2"


def test_config_omits_api_key_header_when_unset() -> None:
    assert "x-api-key" not in OdosConfig().headers()


def test_config_uses_custom_header_name() -> None:
    headers = OdosConfig(api_key="k", api_key_header="Authorization").headers()
    assert headers["Authorization"] == "k"
