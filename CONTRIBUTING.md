# Contributing to odos-py

Thanks for your interest in improving `odos-py`. This guide covers the local
setup and the checks that must pass before a change is merged.

## Development setup

Requires Python 3.9 or newer.

```bash
git clone https://github.com/robertruben98/odos-py.git
cd odos-py
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,exec]"
```

This installs the package in editable mode along with the development tools
(`pytest`, `respx`, `ruff`, `mypy`) and the optional `web3` extra.

## Quality gates

All of these run in CI and must pass locally before opening a PR:

```bash
ruff check .     # lint + import sorting
mypy             # strict type checking (targets Python 3.10)
pytest           # unit tests (HTTP fully mocked, no network)
```

The live integration test is deselected by default; run it explicitly when you
want to exercise the real API:

```bash
pytest -m integration   # hits the keyless GET /info/chains endpoint
```

## Testing conventions

- Unit tests must not touch the network. Mock HTTP with `respx` (or an
  `httpx.MockTransport`).
- New behaviour follows test-driven development: add a failing test first, then
  the implementation.
- Anything that talks to the live API must be marked `@pytest.mark.integration`
  so it stays out of the default suite.

## Code style

- Format and lint with `ruff`; keep the line length at 100.
- Maintain full type hints — `mypy --strict` must stay clean.
- Public functions, methods, and classes use Google-style docstrings
  (Args/Returns/Raises).
- Use `typing.Optional` / `typing.Union` rather than PEP 604 `X | None` in
  runtime-evaluated annotations, since the package supports Python 3.9.

## Submitting changes

1. Branch from `main`.
2. Keep commits focused; do not include AI co-author trailers.
3. Update `CHANGELOG.md` under the `Unreleased` section.
4. Open a PR against `main` and ensure CI is green (including the 3.9 job).
