# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Google-style docstrings (Args/Returns/Raises, with examples on `swap()`)
  across all public sync and async methods, the client constructors,
  `close`/`aclose`, and the exception classes.
- `Field(description=...)` on every request/response model field.
- `CHANGELOG.md`, `CONTRIBUTING.md`, and README status badges.

### Changed
- Documented the payload shape of the info/pricing endpoints (`get_chains`,
  `get_tokens`, `get_router`, `get_contract_info`, `get_token_price`).

### Fixed
- `pyproject.toml` author name (`robertdev` -> `Robert Ruben`).

## [0.1.1] - 2026-06-21

### Fixed
- Corrected `[project.urls]` to point at the real repository
  (`github.com/robertruben98/odos-py`); the previous URLs returned 404. Added
  an `Issues` URL.
- `parse_retry_after` now also parses the RFC 7231 HTTP-date form of the
  `Retry-After` header (in addition to delta-seconds), falling back to
  exponential backoff only when the value is unparseable.

### Added
- Python 3.9 to the CI test matrix to verify real 3.9 support.

## [0.1.0] - 2026-06-21

### Added
- Initial release.
- Synchronous `OdosClient` and asynchronous `AsyncOdosClient`, built on
  `httpx`.
- `pydantic` v2 models for quote and assemble requests/responses.
- Core flow: `quote()` -> `path_id` -> `assemble()`, plus the
  `swap()` / `quote_and_assemble()` helper that chains both.
- Info and pricing endpoints: `get_chains`, `get_tokens`, `get_router`,
  `get_contract_info`, `get_token_price`.
- Optional `api_key` with a configurable header name; automatic HTTP 429
  handling with exponential backoff and `OdosRateLimitError`.
- Configurable `base_url`, full type hints, and a `py.typed` marker.
- Optional `web3` extra (`odos-py[exec]`) for signing/sending the assembled
  transaction.

[Unreleased]: https://github.com/robertruben98/odos-py/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/robertruben98/odos-py/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/robertruben98/odos-py/releases/tag/v0.1.0
