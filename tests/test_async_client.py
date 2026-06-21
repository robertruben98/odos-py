"""Tests for the asynchronous AsyncOdosClient (HTTP mocked via respx)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from odos_py import AsyncOdosClient
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
ASSEMBLE_RESP = {"transaction": {"to": "0xRouter", "data": "0xabc", "chainId": 1}}


def make_quote_request() -> QuoteRequest:
    return QuoteRequest.model_validate(QUOTE_BODY)


@respx.mock
async def test_async_quote_parses_response() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(200, json=QUOTE_RESP)
    )
    async with AsyncOdosClient() as client:
        resp = await client.quote(make_quote_request())

    assert isinstance(resp, QuoteResponse)
    assert resp.path_id == "the-path-id"
    sent = json.loads(route.calls.last.request.content)
    assert sent == QUOTE_BODY


@respx.mock
async def test_async_api_key_header() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        return_value=httpx.Response(200, json=QUOTE_RESP)
    )
    async with AsyncOdosClient(api_key="k", api_key_header="Authorization") as client:
        await client.quote(make_quote_request())
    assert route.calls.last.request.headers["authorization"] == "k"


@respx.mock
async def test_async_swap_chains_quote_then_assemble() -> None:
    respx.post(f"{BASE}/sor/quote/v2").mock(return_value=httpx.Response(200, json=QUOTE_RESP))
    assemble_route = respx.post(f"{BASE}/sor/assemble").mock(
        return_value=httpx.Response(200, json=ASSEMBLE_RESP)
    )
    async with AsyncOdosClient() as client:
        quote, assembled = await client.swap(make_quote_request())

    assert quote.path_id == "the-path-id"
    assert isinstance(assembled, AssembleResponse)
    sent = json.loads(assemble_route.calls.last.request.content)
    assert sent["pathId"] == "the-path-id"


@respx.mock
async def test_async_429_retries_then_succeeds() -> None:
    route = respx.post(f"{BASE}/sor/quote/v2").mock(
        side_effect=[
            httpx.Response(429, json={"detail": "x"}),
            httpx.Response(200, json=QUOTE_RESP),
        ]
    )
    async with AsyncOdosClient(max_retries=3, backoff_base=0.0) as client:
        resp = await client.quote(make_quote_request())
    assert resp.path_id == "the-path-id"
    assert route.call_count == 2


@respx.mock
async def test_async_429_exhausts_and_raises() -> None:
    respx.post(f"{BASE}/sor/quote/v2").mock(return_value=httpx.Response(429, json={"detail": "x"}))
    async with AsyncOdosClient(max_retries=1, backoff_base=0.0) as client:
        with pytest.raises(OdosRateLimitError):
            await client.quote(make_quote_request())


@respx.mock
async def test_async_get_chains() -> None:
    respx.get(f"{BASE}/info/chains").mock(
        return_value=httpx.Response(200, json={"chains": [1, 137]})
    )
    async with AsyncOdosClient() as client:
        data = await client.get_chains()
    assert data == {"chains": [1, 137]}


@respx.mock
async def test_async_non_429_raises_api_error() -> None:
    respx.get(f"{BASE}/info/chains").mock(return_value=httpx.Response(500, json={"detail": "boom"}))
    async with AsyncOdosClient(backoff_base=0.0) as client:
        with pytest.raises(OdosAPIError):
            await client.get_chains()
