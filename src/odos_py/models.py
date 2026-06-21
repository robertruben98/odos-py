"""Pydantic models for Odos API requests and responses.

All models accept both the API's native ``camelCase`` field names and
``snake_case`` aliases so the library is ergonomic from Python while staying
faithful to the wire format. Response models tolerate unknown fields because
the Odos API returns a large, evolving payload.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

_REQUEST_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    serialize_by_alias=True,
)
_RESPONSE_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    extra="allow",
)


class InputToken(BaseModel):
    """A token being sold, with its amount expressed in wei (base units)."""

    model_config = _REQUEST_CONFIG

    token_address: str
    amount: str


class OutputToken(BaseModel):
    """A token being bought, with its desired proportion of the output."""

    model_config = _REQUEST_CONFIG

    token_address: str
    proportion: float


class QuoteRequest(BaseModel):
    """Body for ``POST /sor/quote/v2``."""

    model_config = _REQUEST_CONFIG

    chain_id: int
    input_tokens: list[InputToken]
    output_tokens: list[OutputToken]
    user_addr: str
    slippage_limit_percent: float


class QuoteResponse(BaseModel):
    """Response from ``POST /sor/quote/v2``.

    Only the fields commonly needed by callers are typed explicitly; any other
    fields the API returns are preserved (``extra="allow"``).
    """

    model_config = _RESPONSE_CONFIG

    path_id: Optional[str] = None
    out_amounts: list[str] = Field(default_factory=list)
    in_amounts: list[str] = Field(default_factory=list)
    gas_estimate: Optional[float] = None
    gas_estimate_value: Optional[float] = None
    price_impact: Optional[float] = None
    block_number: Optional[int] = None


class AssembleRequest(BaseModel):
    """Body for ``POST /sor/assemble``."""

    model_config = _REQUEST_CONFIG

    user_addr: str
    path_id: str
    simulate: bool = False


class Transaction(BaseModel):
    """The ready-to-sign transaction returned by ``assemble``."""

    model_config = _RESPONSE_CONFIG

    to: Optional[str] = None
    data: Optional[str] = None
    value: Optional[str] = None
    gas: Optional[int] = None
    gas_price: Optional[int] = None
    nonce: Optional[int] = None
    chain_id: Optional[int] = None
    from_: Optional[str] = Field(default=None, alias="from")


class AssembleResponse(BaseModel):
    """Response from ``POST /sor/assemble``."""

    model_config = _RESPONSE_CONFIG

    transaction: Optional[Transaction] = None
