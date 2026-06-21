"""Tests for pydantic request/response models."""

from __future__ import annotations

from odos_py.models import (
    AssembleRequest,
    AssembleResponse,
    InputToken,
    OutputToken,
    QuoteRequest,
    QuoteResponse,
    Transaction,
)


def test_quote_request_serializes_to_api_body() -> None:
    req = QuoteRequest(
        chainId=1,
        inputTokens=[
            InputToken(
                tokenAddress="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                amount="1000000000000000000",
            )
        ],
        outputTokens=[
            OutputToken(
                tokenAddress="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                proportion=1,
            )
        ],
        userAddr="0x47E2D28169738039755586743E2dfCF3bd643f86",
        slippageLimitPercent=0.3,
    )
    body = req.model_dump(mode="json")
    assert body["chainId"] == 1
    assert body["inputTokens"] == [
        {
            "tokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "amount": "1000000000000000000",
        }
    ]
    assert body["outputTokens"] == [
        {
            "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "proportion": 1,
        }
    ]
    assert body["userAddr"] == "0x47E2D28169738039755586743E2dfCF3bd643f86"
    assert body["slippageLimitPercent"] == 0.3


def test_quote_request_accepts_alias_fields() -> None:
    # Allow snake_case construction via aliases for ergonomics.
    req = QuoteRequest(
        chain_id=137,
        input_tokens=[InputToken(token_address="0xabc", amount="5")],
        output_tokens=[OutputToken(token_address="0xdef", proportion=1)],
        user_addr="0xuser",
        slippage_limit_percent=0.5,
    )
    assert req.chain_id == 137
    assert req.input_tokens[0].token_address == "0xabc"


def test_quote_response_parses_pathid_and_amounts() -> None:
    payload = {
        "pathId": "abc123pathid",
        "outAmounts": ["3500000000"],
        "inAmounts": ["1000000000000000000"],
        "gasEstimate": 250000.0,
        "gasEstimateValue": 12.34,
        "priceImpact": -0.12,
        "blockNumber": 19000000,
    }
    resp = QuoteResponse.model_validate(payload)
    assert resp.path_id == "abc123pathid"
    assert resp.out_amounts == ["3500000000"]
    assert resp.in_amounts == ["1000000000000000000"]
    assert resp.gas_estimate == 250000.0
    assert resp.block_number == 19000000


def test_quote_response_tolerates_extra_fields() -> None:
    # The API returns many fields; unknown ones must not break parsing.
    payload = {"pathId": "p", "outAmounts": ["1"], "someNewField": {"x": 1}}
    resp = QuoteResponse.model_validate(payload)
    assert resp.path_id == "p"


def test_assemble_request_serializes() -> None:
    req = AssembleRequest(userAddr="0xuser", pathId="p123")
    body = req.model_dump(mode="json")
    assert body == {"userAddr": "0xuser", "pathId": "p123", "simulate": False}


def test_assemble_response_parses_transaction() -> None:
    payload = {
        "transaction": {
            "to": "0xRouter",
            "data": "0xdeadbeef",
            "value": "0",
            "gas": 300000,
            "gasPrice": 5000000000,
            "nonce": 7,
            "chainId": 1,
            "from": "0xuser",
        },
        "outputTokens": [{"tokenAddress": "0xdef", "amount": "3500000000"}],
    }
    resp = AssembleResponse.model_validate(payload)
    assert isinstance(resp.transaction, Transaction)
    assert resp.transaction.to == "0xRouter"
    assert resp.transaction.data == "0xdeadbeef"
    assert resp.transaction.chain_id == 1
    assert resp.transaction.nonce == 7
