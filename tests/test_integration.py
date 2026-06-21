"""Live integration smoke tests.

These hit the real Odos API and are deselected by default (see the
``addopts = "-m 'not integration'"`` in pyproject.toml). Run them explicitly:

    pytest -m integration

Only keyless GET ``/info`` endpoints are exercised; the quote endpoint is
intentionally not tested live because it returns HTTP 429 without an API key.
"""

from __future__ import annotations

import pytest

from odos_py import OdosClient

pytestmark = pytest.mark.integration


def test_live_get_chains_returns_supported_chains() -> None:
    with OdosClient() as client:
        data = client.get_chains()
    assert isinstance(data, dict)
    # The API returns a list of supported chain ids under "chains".
    assert "chains" in data
    assert len(data["chains"]) > 0
