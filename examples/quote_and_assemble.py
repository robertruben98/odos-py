"""Quote WETH -> USDC on Ethereum mainnet, then assemble the transaction.

This reproduces the validated flow. The quote endpoint is heavily rate limited
without an API key, so set ODOS_API_KEY to avoid HTTP 429.

    python examples/quote_and_assemble.py
"""

from __future__ import annotations

import os

from odos_py import InputToken, OdosClient, OutputToken, QuoteRequest

WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USER = "0x47E2D28169738039755586743E2dfCF3bd643f86"


def main() -> None:
    client = OdosClient(api_key=os.environ.get("ODOS_API_KEY"))

    request = QuoteRequest(
        chain_id=1,
        input_tokens=[InputToken(token_address=WETH, amount="1000000000000000000")],  # 1 WETH
        output_tokens=[OutputToken(token_address=USDC, proportion=1)],
        user_addr=USER,
        slippage_limit_percent=0.3,
    )

    quote, assembled = client.swap(request)

    print(f"pathId:     {quote.path_id}")
    print(f"out amount: {quote.out_amounts}")
    if assembled.transaction is not None:
        data = assembled.transaction.data
        print(f"tx to:      {assembled.transaction.to}")
        print(f"tx data:    {data[:42] + '...' if data else None}")

    client.close()


if __name__ == "__main__":
    main()
