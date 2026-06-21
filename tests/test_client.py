"""Tests for the synchronous OdosClient (HTTP fully mocked via respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from odos_py import OdosClient
from odos_py.exceptions import OdosAPIError, OdosRateLimitError
from odos_py.models import AssembleResponse, QuoteRequest, QuoteResponse

BASE = "https://api.odos.xyz"

QUOTE_BODY = {
    "chainId": 1,
    "inputTokens": [
        {
            "tokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "amount": "1000000000000000000",
        }
    ],
    "outputTokens": [
        {
            "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "proportion": 1,
        }
    ],
    "userAddr": "0x47E2D28169738039755586743E2dfCF3bd643f86",
    "slippageLimitPercent": 0.3,
}

QUOTE_RESP = {"pathId": "the-path-id", "outAmounts": ["3500000000"]}
ASSEMBLE_RESP = {"transaction": {"to": "0xRouter", "data": "0xabc", "value": "0", "chainId": 1}}


def make_quote_request() -> QuoteRequest:
    return QuoteRequest.model_validate(QUOTE_BODY)


def test_default_base_url() -> None:
    client = OdosClient()
    assert client.base_url == BASE


def test_base_url_is_configurable_and_trailing_slash_stripped() -> None:
    client = OdosClient(base_url="https://proxy.example.com/")
    assert client.base_url == "https://proxy.example.com"


@respx.mock
def test_quote_sends_body_and_parses_response() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(200, json=QUOTE_RESP)
    )
    client = OdosClient()
    resp = client.quote(make_quote_request())

    assert route.called
    assert isinstance(resp, QuoteResponse)
    assert resp.path_id == "the-path-id"
    # The wire body must be camelCase exactly as the API expects.
    import json

    sent = json.loads(route.calls.last.request.content)
    assert sent == QUOTE_BODY


@respx.mock
def test_api_key_sent_in_default_header() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(200, json=QUOTE_RESP)
    )
    client = OdosClient(api_key="secret-key")
    client.quote(make_quote_request())

    assert route.calls.last.request.headers["x-api-key"] == "secret-key"


@respx.mock
def test_api_key_header_name_is_overridable() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(200, json=QUOTE_RESP)
    )
    client = OdosClient(api_key="secret-key", api_key_header="Authorization")
    client.quote(make_quote_request())

    assert route.calls.last.request.headers["authorization"] == "secret-key"


@respx.mock
def test_no_api_key_header_when_unset() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(200, json=QUOTE_RESP)
    )
    client = OdosClient()
    client.quote(make_quote_request())

    assert "x-api-key" not in route.calls.last.request.headers


@respx.mock
def test_assemble_sends_body_and_parses_transaction() -> None:
    route = respx.post(f"{BASE}/sor/assemble").mock(
        return_value=httpx.Response(200, json=ASSEMBLE_RESP)
    )
    client = OdosClient()
    resp = client.assemble(user_addr="0xuser", path_id="the-path-id")

    assert isinstance(resp, AssembleResponse)
    assert resp.transaction is not None
    assert resp.transaction.to == "0xRouter"

    import json

    sent = json.loads(route.calls.last.request.content)
    assert sent == {"userAddr": "0xuser", "pathId": "the-path-id", "simulate": False}


@respx.mock
def test_swap_chains_quote_then_assemble() -> None:
    respx.post(f"{BASE}/sor/quote/v2").mock(return_value=httpx.Response(200, json=QUOTE_RESP))
    assemble_route = respx.post(f"{BASE}/sor/assemble").mock(
        return_value=httpx.Response(200, json=ASSEMBLE_RESP)
    )
    client = OdosClient()
    quote, assembled = client.swap(make_quote_request())

    assert quote.path_id == "the-path-id"
    assert assembled.transaction is not None
    assert assembled.transaction.to == "0xRouter"

    import json

    sent = json.loads(assemble_route.calls.last.request.content)
    # The pathId from the quote must be threaded into assemble automatically.
    assert sent["pathId"] == "the-path-id"
    assert sent["userAddr"] == QUOTE_BODY["userAddr"]


@respx.mock
def test_swap_raises_if_quote_has_no_path_id() -> None:
    respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(200, json={"outAmounts": []})
    )
    client = OdosClient()
    with pytest.raises(OdosAPIError):
        client.swap(make_quote_request())


@respx.mock
def test_429_retries_then_succeeds() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        side_effect=[
            httpx.Response(429, json={"detail": "rate limited"}),
            httpx.Response(429, json={"detail": "rate limited"}),
            httpx.Response(200, json=QUOTE_RESP),
        ]
    )
    # backoff_base=0 keeps the test instant.
    client = OdosClient(max_retries=3, backoff_base=0.0)
    resp = client.quote(make_quote_request())

    assert resp.path_id == "the-path-id"
    assert route.call_count == 3


@respx.mock
def test_429_exhausts_retries_and_raises_rate_limit_error() -> None:
    respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(429, json={"detail": "rate limited"})
    )
    client = OdosClient(max_retries=2, backoff_base=0.0)
    with pytest.raises(OdosRateLimitError) as exc_info:
        client.quote(make_quote_request())
    assert exc_info.value.status_code == 429


@respx.mock
def test_non_429_error_raises_api_error_without_retry() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(400, json={"detail": "bad request"})
    )
    client = OdosClient(max_retries=3, backoff_base=0.0)
    with pytest.raises(OdosAPIError) as exc_info:
        client.quote(make_quote_request())
    assert exc_info.value.status_code == 400
    assert route.call_count == 1  # 4xx (non-429) is not retried


@respx.mock
def test_get_chains() -> None:
    respx.get(f"{BASE}/info/chains").mock(
        return_value=httpx.Response(200, json={"chains": [1, 137, 8453]})
    )
    client = OdosClient()
    data = client.get_chains()
    assert data == {"chains": [1, 137, 8453]}


@respx.mock
def test_get_tokens() -> None:
    respx.get(f"{BASE}/info/tokens/1").mock(
        return_value=httpx.Response(200, json={"tokenMap": {"0xabc": {"symbol": "WETH"}}})
    )
    client = OdosClient()
    data = client.get_tokens(1)
    assert "tokenMap" in data


@respx.mock
def test_get_router_address() -> None:
    respx.get(f"{BASE}/info/router/v2/1").mock(
        return_value=httpx.Response(200, json={"address": "0xRouter"})
    )
    client = OdosClient()
    data = client.get_router(1)
    assert data["address"] == "0xRouter"


@respx.mock
def test_get_token_price() -> None:
    respx.get(f"{BASE}/pricing/token/1/0xabc").mock(
        return_value=httpx.Response(200, json={"price": 3500.0})
    )
    client = OdosClient()
    data = client.get_token_price(1, "0xabc")
    assert data["price"] == 3500.0


@respx.mock
def test_context_manager_closes_cleanly() -> None:
    respx.get(f"{BASE}/info/chains").mock(return_value=httpx.Response(200, json={"chains": [1]}))
    with OdosClient() as client:
        assert client.get_chains() == {"chains": [1]}
