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
    """A token being sold, with its amount expressed in wei (base units).

    Attributes:
        token_address: Checksummed ERC-20 contract address of the token being
            sold. Serialized as ``tokenAddress``.
        amount: Amount to sell, as a decimal string in the token's smallest
            unit (wei for an 18-decimal token). A string is used to avoid
            precision loss on large integers.
    """

    model_config = _REQUEST_CONFIG

    token_address: str = Field(
        description="Checksummed ERC-20 contract address of the token being sold.",
    )
    amount: str = Field(
        description="Amount to sell, as a decimal string in the token's smallest unit (wei).",
    )


class OutputToken(BaseModel):
    """A token being bought, with its desired proportion of the output.

    Attributes:
        token_address: Checksummed ERC-20 contract address of the token to
            receive. Serialized as ``tokenAddress``.
        proportion: Share of the total output this token should represent, in
            the range ``0..1``. Proportions across all output tokens should
            sum to ``1`` (use ``1`` for a single-output swap).
    """

    model_config = _REQUEST_CONFIG

    token_address: str = Field(
        description="Checksummed ERC-20 contract address of the token to receive.",
    )
    proportion: float = Field(
        description="Share of total output for this token (0..1); all proportions sum to 1.",
    )


class QuoteRequest(BaseModel):
    """Body for ``POST /sor/quote/v2``.

    Describes the swap to price. The response (:class:`QuoteResponse`) carries
    the ``path_id`` that :meth:`~odos_py.OdosClient.assemble` turns into
    signable calldata.

    Attributes:
        chain_id: EVM chain id the swap executes on (e.g. ``1`` for Ethereum
            mainnet, ``137`` for Polygon). Serialized as ``chainId``.
        input_tokens: Tokens being sold and their amounts (in wei).
        output_tokens: Tokens to receive and their output proportions.
        user_addr: Address that will execute the swap; also receives the
            output tokens. Serialized as ``userAddr``.
        slippage_limit_percent: Maximum acceptable slippage as a percentage
            (e.g. ``0.3`` means 0.3%). Serialized as ``slippageLimitPercent``.
    """

    model_config = _REQUEST_CONFIG

    chain_id: int = Field(
        description="EVM chain id the swap executes on (1 = Ethereum mainnet).",
    )
    input_tokens: list[InputToken] = Field(
        description="Tokens being sold and their amounts (in wei).",
    )
    output_tokens: list[OutputToken] = Field(
        description="Tokens to receive and their output proportions.",
    )
    user_addr: str = Field(
        description="Address that executes the swap and receives the output tokens.",
    )
    slippage_limit_percent: float = Field(
        description="Maximum acceptable slippage as a percentage (0.3 = 0.3%).",
    )


class QuoteResponse(BaseModel):
    """Response from ``POST /sor/quote/v2``.

    Only the fields commonly needed by callers are typed explicitly; any other
    fields the API returns are preserved (``extra="allow"``) and accessible via
    ``model_extra``.

    Attributes:
        path_id: Opaque identifier for the routed path. Pass it to
            :meth:`~odos_py.OdosClient.assemble` to build the transaction.
            ``None`` if the quote produced no executable path.
        out_amounts: Expected output amounts (wei), parallel to the request's
            ``output_tokens``.
        in_amounts: Input amounts consumed (wei), parallel to ``input_tokens``.
        gas_estimate: Estimated gas units for the swap.
        gas_estimate_value: Estimated gas cost expressed in USD.
        price_impact: Estimated price impact of the swap, as a percentage
            (may be negative).
        block_number: Block height the quote was computed against.
    """

    model_config = _RESPONSE_CONFIG

    path_id: Optional[str] = Field(
        default=None,
        description="Opaque path identifier to pass to assemble; None if no path was found.",
    )
    out_amounts: list[str] = Field(
        default_factory=list,
        description="Expected output amounts (wei), parallel to output_tokens.",
    )
    in_amounts: list[str] = Field(
        default_factory=list,
        description="Input amounts consumed (wei), parallel to input_tokens.",
    )
    gas_estimate: Optional[float] = Field(
        default=None, description="Estimated gas units for the swap."
    )
    gas_estimate_value: Optional[float] = Field(
        default=None, description="Estimated gas cost in USD."
    )
    price_impact: Optional[float] = Field(
        default=None, description="Estimated price impact percentage (may be negative)."
    )
    block_number: Optional[int] = Field(
        default=None, description="Block height the quote was computed against."
    )


class AssembleRequest(BaseModel):
    """Body for ``POST /sor/assemble``.

    Attributes:
        user_addr: Address that will execute the swap. Must match the
            ``user_addr`` used for the originating quote. Serialized as
            ``userAddr``.
        path_id: The ``path_id`` returned by a prior quote. Serialized as
            ``pathId``.
        simulate: When ``True``, asks Odos to simulate the transaction and
            return the simulation result alongside the calldata.
    """

    model_config = _REQUEST_CONFIG

    user_addr: str = Field(
        description="Address that executes the swap; must match the quote's user_addr.",
    )
    path_id: str = Field(
        description="The path_id returned by a prior quote.",
    )
    simulate: bool = Field(
        default=False,
        description="If True, ask Odos to simulate the transaction before returning it.",
    )


class Transaction(BaseModel):
    """The ready-to-sign transaction returned by ``assemble``.

    The fields mirror a standard EVM transaction and can be passed to a signer
    such as ``web3.py``'s ``eth.account.sign_transaction``. All fields are
    optional because the API may omit some depending on the request.

    Attributes:
        to: Router contract address the transaction calls.
        data: ABI-encoded calldata (``0x``-prefixed hex).
        value: Native-token amount to send with the call (wei, as a string).
        gas: Gas limit.
        gas_price: Gas price in wei. Serialized as ``gasPrice``.
        nonce: Sender account nonce.
        chain_id: EVM chain id the transaction targets. Serialized as
            ``chainId``.
        from_: Sender address. Serialized as ``from`` (renamed because ``from``
            is a Python keyword).
    """

    model_config = _RESPONSE_CONFIG

    to: Optional[str] = Field(
        default=None, description="Router contract address the transaction calls."
    )
    data: Optional[str] = Field(default=None, description="ABI-encoded calldata (0x-prefixed hex).")
    value: Optional[str] = Field(
        default=None, description="Native-token amount to send (wei, as a string)."
    )
    gas: Optional[int] = Field(default=None, description="Gas limit.")
    gas_price: Optional[int] = Field(default=None, description="Gas price in wei.")
    nonce: Optional[int] = Field(default=None, description="Sender account nonce.")
    chain_id: Optional[int] = Field(
        default=None, description="EVM chain id the transaction targets."
    )
    from_: Optional[str] = Field(default=None, alias="from", description="Sender address.")


class AssembleResponse(BaseModel):
    """Response from ``POST /sor/assemble``.

    Any fields the API returns beyond ``transaction`` (e.g. simulation output,
    expected output amounts) are preserved via ``extra="allow"`` and reachable
    through ``model_extra``.

    Attributes:
        transaction: The ready-to-sign :class:`Transaction`, or ``None`` if the
            API did not return one.
    """

    model_config = _RESPONSE_CONFIG

    transaction: Optional[Transaction] = Field(
        default=None, description="The ready-to-sign transaction, if returned."
    )
