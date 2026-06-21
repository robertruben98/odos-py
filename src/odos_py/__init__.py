"""odos-py: a modern Python client for the Odos DEX Aggregator API."""

from __future__ import annotations

from .async_client import AsyncOdosClient
from .client import OdosClient
from .exceptions import OdosAPIError, OdosError, OdosRateLimitError
from .models import (
    AssembleRequest,
    AssembleResponse,
    InputToken,
    OutputToken,
    QuoteRequest,
    QuoteResponse,
    Transaction,
)

__version__ = "0.1.0"

__all__ = [
    "OdosClient",
    "AsyncOdosClient",
    "OdosError",
    "OdosAPIError",
    "OdosRateLimitError",
    "QuoteRequest",
    "QuoteResponse",
    "AssembleRequest",
    "AssembleResponse",
    "InputToken",
    "OutputToken",
    "Transaction",
]
