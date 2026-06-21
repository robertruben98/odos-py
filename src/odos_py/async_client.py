"""Asynchronous client for the Odos DEX Aggregator API."""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any, Optional

import httpx

from ._base import (
    DEFAULT_API_KEY_HEADER,
    DEFAULT_BACKOFF_BASE,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    OdosConfig,
    backoff_delay,
    parse_retry_after,
    safe_json,
)
from .exceptions import OdosAPIError, OdosRateLimitError
from .models import AssembleRequest, AssembleResponse, QuoteRequest, QuoteResponse


class AsyncOdosClient:
    """Async counterpart of :class:`~odos_py.client.OdosClient`.

    Same configuration and behaviour, backed by ``httpx.AsyncClient``.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        api_key_header: str = DEFAULT_API_KEY_HEADER,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._config = OdosConfig(
            base_url=base_url,
            api_key=api_key,
            api_key_header=api_key_header,
            max_retries=max_retries,
            backoff_base=backoff_base,
            timeout=timeout,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers=self._config.headers(),
            transport=transport,
        )

    @property
    def base_url(self) -> str:
        return self._config.base_url

    # -- lifecycle ---------------------------------------------------------

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOdosClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    # -- low-level request with retry/backoff ------------------------------

    async def _request(self, method: str, path: str, *, json: Any = None) -> Any:
        url = self._config.url(path)
        attempt = 0
        while True:
            response = await self._client.request(method, url, json=json)
            if response.status_code < 400:
                return safe_json(response)

            if response.status_code == 429 and attempt < self._config.max_retries:
                retry_after = parse_retry_after(response.headers)
                delay = backoff_delay(self._config.backoff_base, attempt, retry_after)
                if delay > 0:
                    await asyncio.sleep(delay)
                attempt += 1
                continue

            body = safe_json(response)
            message = f"{method} {url} failed with status {response.status_code}"
            if response.status_code == 429:
                raise OdosRateLimitError(
                    message,
                    status_code=429,
                    body=body,
                    retry_after=parse_retry_after(response.headers),
                )
            raise OdosAPIError(message, status_code=response.status_code, body=body)

    # -- SOR endpoints -----------------------------------------------------

    async def quote(self, request: QuoteRequest) -> QuoteResponse:
        """``POST /sor/quote/v2`` — get a swap path and its ``pathId``."""
        data = await self._request("POST", "/sor/quote/v2", json=request.model_dump(by_alias=True))
        return QuoteResponse.model_validate(data)

    async def assemble(
        self, *, user_addr: str, path_id: str, simulate: bool = False
    ) -> AssembleResponse:
        """``POST /sor/assemble`` — turn a ``pathId`` into signable calldata."""
        req = AssembleRequest(user_addr=user_addr, path_id=path_id, simulate=simulate)
        data = await self._request("POST", "/sor/assemble", json=req.model_dump(by_alias=True))
        return AssembleResponse.model_validate(data)

    async def execute(self, *, user_addr: str, path_id: str) -> Any:
        """``POST /sor/execute`` — assisted execution (returns raw JSON)."""
        return await self._request(
            "POST",
            "/sor/execute",
            json={"userAddr": user_addr, "pathId": path_id},
        )

    async def swap(
        self, request: QuoteRequest, *, simulate: bool = False
    ) -> tuple[QuoteResponse, AssembleResponse]:
        """Convenience helper: quote then assemble in one awaited call."""
        quote = await self.quote(request)
        if not quote.path_id:
            raise OdosAPIError("Quote response did not include a pathId", body=quote.model_dump())
        assembled = await self.assemble(
            user_addr=request.user_addr, path_id=quote.path_id, simulate=simulate
        )
        return quote, assembled

    quote_and_assemble = swap

    # -- info / pricing endpoints -----------------------------------------

    async def get_chains(self) -> Any:
        """``GET /info/chains`` — supported chains."""
        return await self._request("GET", "/info/chains")

    async def get_tokens(self, chain_id: int) -> Any:
        """``GET /info/tokens/{chainId}`` — token map for a chain."""
        return await self._request("GET", f"/info/tokens/{chain_id}")

    async def get_router(self, chain_id: int) -> Any:
        """``GET /info/router/v2/{chainId}`` — router contract address."""
        return await self._request("GET", f"/info/router/v2/{chain_id}")

    async def get_contract_info(self, chain_id: int) -> Any:
        """``GET /info/contract-info/v2/{chainId}`` — contract metadata."""
        return await self._request("GET", f"/info/contract-info/v2/{chain_id}")

    async def get_token_price(self, chain_id: int, token_address: str) -> Any:
        """``GET /pricing/token/{chainId}/{tokenAddress}`` — token price."""
        return await self._request("GET", f"/pricing/token/{chain_id}/{token_address}")
