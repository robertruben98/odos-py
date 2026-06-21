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

    Same configuration and behaviour, backed by ``httpx.AsyncClient``. The core
    flow is identical: :meth:`quote` returns a ``path_id``, :meth:`assemble`
    turns it into signable calldata, and :meth:`swap` chains both.

    Use it as an async context manager so the connection pool is closed::

        async with AsyncOdosClient(api_key="...") as client:
            quote = await client.quote(request)

    Example:
        >>> async with AsyncOdosClient() as client:
        ...     chains = await client.get_chains()
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
        """Create an async client.

        Args:
            base_url: Base URL of the Odos API. Override to target a proxy or a
                self-hosted gateway.
            api_key: Optional API key. Strongly recommended: the keyless tier
                is heavily rate limited.
            api_key_header: Header name the ``api_key`` is sent under. The real
                header name is undocumented, so it is configurable (e.g.
                ``"Authorization"``).
            max_retries: Maximum number of automatic retries on HTTP 429.
            backoff_base: Base delay (seconds) for exponential backoff between
                429 retries.
            timeout: Per-request timeout in seconds.
            transport: Optional custom ``httpx`` async transport, primarily for
                testing (e.g. a ``MockTransport``).
        """
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
        """Close the underlying async HTTP connection pool.

        Safe to await multiple times. Called automatically when the client is
        used as an async context manager.
        """
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
        """Request a swap quote (``POST /sor/quote/v2``).

        Prices the swap described by ``request`` and returns the best path,
        including the ``path_id`` needed by :meth:`assemble`.

        Args:
            request: The swap to price.

        Returns:
            The parsed quote, whose ``path_id`` feeds :meth:`assemble`.

        Raises:
            OdosRateLimitError: If rate limited (HTTP 429) past ``max_retries``.
            OdosAPIError: For any other non-success HTTP status.
        """
        data = await self._request("POST", "/sor/quote/v2", json=request.model_dump(by_alias=True))
        return QuoteResponse.model_validate(data)

    async def assemble(
        self, *, user_addr: str, path_id: str, simulate: bool = False
    ) -> AssembleResponse:
        """Assemble a quoted path into a signable transaction (``POST /sor/assemble``).

        Args:
            user_addr: Address that will execute the swap. Must match the
                ``user_addr`` used for the originating quote.
            path_id: The ``path_id`` returned by a prior :meth:`quote`.
            simulate: If ``True``, ask Odos to simulate the transaction and
                include the result in the response.

        Returns:
            The assembled response; ``transaction`` holds the ready-to-sign
            EVM transaction.

        Raises:
            OdosRateLimitError: If rate limited (HTTP 429) past ``max_retries``.
            OdosAPIError: For any other non-success HTTP status.
        """
        req = AssembleRequest(user_addr=user_addr, path_id=path_id, simulate=simulate)
        data = await self._request("POST", "/sor/assemble", json=req.model_dump(by_alias=True))
        return AssembleResponse.model_validate(data)

    async def execute(self, *, user_addr: str, path_id: str) -> Any:
        """Request assisted execution of a quoted path (``POST /sor/execute``).

        Args:
            user_addr: Address that will execute the swap.
            path_id: The ``path_id`` returned by a prior :meth:`quote`.

        Returns:
            The raw decoded JSON payload from the API (shape not modelled).

        Raises:
            OdosRateLimitError: If rate limited (HTTP 429) past ``max_retries``.
            OdosAPIError: For any other non-success HTTP status.
        """
        return await self._request(
            "POST",
            "/sor/execute",
            json={"userAddr": user_addr, "pathId": path_id},
        )

    async def swap(
        self, request: QuoteRequest, *, simulate: bool = False
    ) -> tuple[QuoteResponse, AssembleResponse]:
        """Quote then assemble a swap in a single awaited call.

        Convenience helper that runs :meth:`quote`, threads the resulting
        ``path_id`` into :meth:`assemble`, and returns both.

        Args:
            request: The swap to quote and assemble.
            simulate: Forwarded to :meth:`assemble`; if ``True``, Odos
                simulates the transaction.

        Returns:
            A ``(quote, assembled)`` tuple: the :class:`QuoteResponse` and the
            :class:`AssembleResponse` whose ``transaction`` is ready to sign.

        Raises:
            OdosAPIError: If the quote returned no ``path_id``, or on any
                non-success HTTP status.
            OdosRateLimitError: If rate limited (HTTP 429) past ``max_retries``.

        Example:
            >>> async with AsyncOdosClient() as client:
            ...     quote, assembled = await client.swap(request)
            ...     assembled.transaction.to  # router contract address
        """
        quote = await self.quote(request)
        if not quote.path_id:
            raise OdosAPIError("Quote response did not include a pathId", body=quote.model_dump())
        assembled = await self.assemble(
            user_addr=request.user_addr, path_id=quote.path_id, simulate=simulate
        )
        return quote, assembled

    quote_and_assemble = swap
    """Alias for :meth:`swap`: quote then assemble in one awaited call."""

    # -- info / pricing endpoints -----------------------------------------

    async def get_chains(self) -> Any:
        """List supported chains (``GET /info/chains``).

        Returns:
            Decoded JSON of the form ``{"chains": [<chain_id>, ...]}`` listing
            the EVM chain ids Odos supports.

        Raises:
            OdosAPIError: On any non-success HTTP status.
        """
        return await self._request("GET", "/info/chains")

    async def get_tokens(self, chain_id: int) -> Any:
        """List tokens for a chain (``GET /info/tokens/{chainId}``).

        Args:
            chain_id: EVM chain id to list tokens for.

        Returns:
            Decoded JSON of the form ``{"tokenMap": {<address>: {"symbol":
            ..., "decimals": ..., "name": ...}, ...}}`` keyed by token address.

        Raises:
            OdosAPIError: On any non-success HTTP status.
        """
        return await self._request("GET", f"/info/tokens/{chain_id}")

    async def get_router(self, chain_id: int) -> Any:
        """Get the router contract address for a chain (``GET /info/router/v2/{chainId}``).

        Args:
            chain_id: EVM chain id to look up.

        Returns:
            Decoded JSON containing the router contract ``address`` for the
            chain.

        Raises:
            OdosAPIError: On any non-success HTTP status.
        """
        return await self._request("GET", f"/info/router/v2/{chain_id}")

    async def get_contract_info(self, chain_id: int) -> Any:
        """Get router contract metadata for a chain (``GET /info/contract-info/v2/{chainId}``).

        Args:
            chain_id: EVM chain id to look up.

        Returns:
            Decoded JSON with contract metadata (address and related details)
            for the chain.

        Raises:
            OdosAPIError: On any non-success HTTP status.
        """
        return await self._request("GET", f"/info/contract-info/v2/{chain_id}")

    async def get_token_price(self, chain_id: int, token_address: str) -> Any:
        """Get the price of a token (``GET /pricing/token/{chainId}/{tokenAddress}``).

        Args:
            chain_id: EVM chain id the token lives on.
            token_address: ERC-20 contract address of the token.

        Returns:
            Decoded JSON of the form ``{"price": <float>, ...}`` giving the
            token's USD price.

        Raises:
            OdosAPIError: On any non-success HTTP status.
        """
        return await self._request("GET", f"/pricing/token/{chain_id}/{token_address}")
