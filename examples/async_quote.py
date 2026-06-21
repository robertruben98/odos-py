"""Async variant: quote WETH -> USDC on Ethereum mainnet.

python examples/async_quote.py
"""

from __future__ import annotations

import asyncio
import os

from odos_py import AsyncOdosClient, InputToken, OutputToken, QuoteRequest

WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USER = "0x47E2D28169738039755586743E2dfCF3bd643f86"


async def main() -> None:
    request = QuoteRequest(
        chain_id=1,
        input_tokens=[InputToken(token_address=WETH, amount="1000000000000000000")],
        output_tokens=[OutputToken(token_address=USDC, proportion=1)],
        user_addr=USER,
        slippage_limit_percent=0.3,
    )

    async with AsyncOdosClient(api_key=os.environ.get("ODOS_API_KEY")) as client:
        quote = await client.quote(request)
        print(f"pathId:     {quote.path_id}")
        print(f"out amount: {quote.out_amounts}")


if __name__ == "__main__":
    asyncio.run(main())
