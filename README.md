# odos-py

[![CI](https://github.com/robertruben98/odos-py/actions/workflows/ci.yml/badge.svg)](https://github.com/robertruben98/odos-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/odos-py.svg)](https://pypi.org/project/odos-py/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://robertruben98.github.io/odos-py/)
[![Python](https://img.shields.io/pypi/pyversions/odos-py.svg)](https://pypi.org/project/odos-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, fully-typed Python client for the [Odos](https://docs.odos.xyz/build/api-docs) DEX Aggregator API.

- Sync (`OdosClient`) and async (`AsyncOdosClient`) clients built on `httpx`
- `pydantic` v2 models for all requests and responses
- Automatic HTTP 429 handling with exponential backoff
- Configurable base URL and API-key header
- `mypy --strict` clean, ships a `py.typed` marker

## Install

```bash
pip install odos-py
```

Optional extra for signing/sending the assembled transaction with `web3.py`:

```bash
pip install "odos-py[exec]"
```

## Quickstart

Odos works in two steps: `quote` returns a `pathId`, then `assemble` turns that
`pathId` into ready-to-sign transaction calldata. The `swap()` helper chains
both:

```python
from odos_py import OdosClient, QuoteRequest, InputToken, OutputToken

client = OdosClient(api_key="YOUR_KEY")  # api_key optional but recommended
quote, assembled = client.swap(QuoteRequest(
    chain_id=1,
    input_tokens=[InputToken(token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                             amount="1000000000000000000")],                              # 1 WETH (wei)
    output_tokens=[OutputToken(token_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
                               proportion=1)],
    user_addr="0x47E2D28169738039755586743E2dfCF3bd643f86",
    slippage_limit_percent=0.3,
))
print(quote.path_id, assembled.transaction.to)
```

Async is identical with `await`:

```python
import asyncio
from odos_py import AsyncOdosClient

async def main(request):
    async with AsyncOdosClient() as client:
        quote = await client.quote(request)
        print(quote.path_id)
```

## Auth & rate limits

There is a free, **keyless** tier, but it is heavily rate limited — `POST
/sor/quote/v2` returns HTTP 429 quickly without a key. Pass an `api_key` to
raise limits. The exact API-key header name is not publicly documented, so it
is configurable:

```python
OdosClient(api_key="YOUR_KEY", api_key_header="x-api-key")  # default header name
```

The client retries 429 responses with exponential backoff (honouring any
`Retry-After` header) and raises `OdosRateLimitError` once retries are
exhausted. Tune with `max_retries` and `backoff_base`.

## Endpoints

| Method | Endpoint |
| --- | --- |
| `quote(request)` | `POST /sor/quote/v2` |
| `assemble(user_addr=, path_id=)` | `POST /sor/assemble` |
| `execute(user_addr=, path_id=)` | `POST /sor/execute` |
| `swap(request)` / `quote_and_assemble(request)` | quote then assemble |
| `get_chains()` | `GET /info/chains` |
| `get_tokens(chain_id)` | `GET /info/tokens/{chainId}` |
| `get_router(chain_id)` | `GET /info/router/v2/{chainId}` |
| `get_contract_info(chain_id)` | `GET /info/contract-info/v2/{chainId}` |
| `get_token_price(chain_id, token_address)` | `GET /pricing/token/{chainId}/{tokenAddress}` |

Multi-chain is handled per call via `chain_id` on `QuoteRequest` and the info
endpoints.

## Configuration

```python
OdosClient(
    base_url="https://api.odos.xyz",  # configurable / proxyable
    api_key=None,
    api_key_header="x-api-key",
    max_retries=3,
    backoff_base=0.5,
    timeout=30.0,
)
```

## Development

```bash
pip install -e ".[dev,exec]"
pytest                  # unit tests (HTTP mocked, no network)
pytest -m integration   # live smoke test against /info/chains
ruff check .
mypy
```

## License

MIT
