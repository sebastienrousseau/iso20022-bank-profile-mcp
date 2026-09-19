# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `--transport streamable-http` and `--transport sse`, with `--host` and
  `--port`. Streamable HTTP serves both current protocol revisions
  (2026-07-28 stateless with `server/discover`, and 2025-11-25 with the
  `initialize` handshake) on one endpoint and streams responses as
  server-sent events; `sse` serves the older HTTP+SSE transport. stdio
  stays the default and is unchanged, and so is the authenticated
  `--transport http` with `--bind`. ADR 0001 records the decision.
- Governance parity with the suite: `ARCHITECTURE.md`, `RELEASING.md`,
  `CITATION.cff`, `DCO.txt` with a Developer Certificate of Origin check
  on every pull request, and `docs/adr/`.

### Fixed

- The Glama and MCP-registry manifests (`glama.json`, `server.json`) named a
  release several versions old, so the directory listings advertised a stale
  install; both are stamped to the shipped version and a CI job now fails
  when they, the package version and the changelog disagree.

## [0.0.5] - 2026-08-29

Adds the scheduled release-consistency check this repository was
missing, and refreshes the shared conformance gate.

### Added

- `scripts/check_suite_consistency.py` and a scheduled **Release
  Consistency** workflow compare this tree against what is actually
  published on PyPI. A version bumped in the tree and never released
  breaks nothing — the tree is consistent, the tests pass, the changelog
  is written — and only the index disagrees. That has happened three
  times in this suite, each time stranding a security floor that reached
  nobody.
- The check distinguishes the two directions: a tree ahead of the index
  is the expected transient between merging a bump and pushing its tag,
  while a tree *behind* it means a release was cut from somewhere other
  than this branch.

### Changed

- Refreshed `tests/test_suite_conformance.py` to the current canonical
  copy. This repository was carrying a 24-invariant version; the
  twenty-fifth is the one that requires the check added above, so it had
  been conformant only against an older bar.

## [0.0.4] - 2026-08-28

Brings this repository onto the **suite conformance gate**.

### Added

- **`benches/bench_lint_payload.py`** — what linting costs, and how it
  grows. An agent working a folder calls `lint_payload` once per file, and
  a corporate batch is hundreds of `<PmtInf>` blocks, not one.

  Two things it already confirms:

  **Linting is linear.** `us/block` moves **1.04x** between 10 and 5,000
  blocks, so the linter makes one pass over the tree rather than
  re-walking it per rule. Fixtures are all small and would never have
  shown the difference.

  **The entitlement gate refuses before doing the work.** A gated profile
  is refused in **0.006 ms** against **0.33 ms** for the cheapest
  permitted one. That is the right way round: a gate that lints first and
  discards the answer wastes the work *and* leaks timing about rules the
  caller is not entitled to see. It was never measured before.

  Nothing asserts a timing threshold — wall-clock is not comparable
  between machines, and a flaky performance gate teaches people to ignore
  red. CI runs `--quick`, so a benchmark that stops compiling fails the
  build rather than rotting.

- **`tests/test_suite_conformance.py`** — invariants shared by every
  repository in the suite, vendored from one canonical copy and
  checksummed by its own test. Editing the local copy fails by design.

### Changed

- CI lints, formats and runs `benches/` alongside everything else.
- `tomli` (on 3.10) and `packaging` are declared dev dependencies rather
  than relied on transitively via pytest. The conformance gate parses
  `pyproject.toml`, and a gate that silently stops running is worse than
  no gate.
- `tests/test_suite_conformance.py` is excluded from black: it is
  generated, and the suite uses three different line lengths.

## [0.0.3] - 2026-08-21

### Added

- **MCP prompts and resources** for parity across the MCP trinity, so
  this server exposes the same surface shape as its siblings.
- **Optional OpenTelemetry tracing** behind the `[otel]` extra.

### Fixed

- **`cryptography` 50.0.0**, the release that patches the outstanding
  advisory. The previous ceiling made it unresolvable.
- **`mcp` capped below 2.0**, restoring the FastMCP API the server is
  written against.

### Changed

- **Adopted the shared MCP compatibility layer.**
- **A `lockfile` CI job.** `release.yml` installs with poetry and CI did
  not, so a stale `poetry.lock` was undetectable until a release — with
  the tag already public. The same gap turned a sibling package's
  release red at its first step.
- Dependency and GitHub Actions updates consolidated across several
  Dependabot batches.

## [0.0.2] - 2026-07-18

Adds an **optional streamable-HTTP transport** with OAuth 2.1 resource-server
authentication for shared, multi-tenant deployments, and **premium rule-pack
entitlement gating** so higher-tier, licensed clearing profiles can be served
alongside the open baseline. The default transport is unchanged — stdio, one
process per operator, no network surface — and the open baseline profiles stay
unrestricted.

### Added

- **Optional streamable-HTTP transport**:
  `iso20022-bank-profile-mcp --transport=http --bind=HOST:PORT` serves the
  MCP session over HTTP (default `--bind` `127.0.0.1:8080`, loopback-only, so
  exposing it beyond the host is an explicit opt-in). stdio remains the
  default transport.
- **OAuth 2.1 resource-server auth (RFC 9728)** on the HTTP transport: set
  `ISO20022_BANK_PROFILE_OAUTH_ISSUER` and `ISO20022_BANK_PROFILE_OAUTH_AUDIENCE`
  (with optional `ISO20022_BANK_PROFILE_OAUTH_JWKS_URL`, defaulting to
  `<issuer>/.well-known/jwks.json`, and `ISO20022_BANK_PROFILE_OAUTH_SCOPES`)
  to validate `Authorization: Bearer` JWTs against the JWKS, `iss`, `aud`,
  `exp`, `nbf`, and any required scopes. Failures are rejected `401` / `403`
  with an RFC 9728 `WWW-Authenticate` challenge, and protected-resource
  metadata is served at `/.well-known/oauth-protected-resource`. A static
  dev-mode bearer token (`ISO20022_BANK_PROFILE_TOKEN`) remains available as a
  fallback; starting the HTTP transport with **no** auth configured is refused.
  An optional `X-MCP-Tenant` request header is forwarded into the tool-visible
  request context. New runtime dependencies: `pyjwt[crypto]`, `httpx`,
  `starlette`, `uvicorn`.
- **Premium rule-pack entitlement gating**: clearing profiles now carry a
  `tier` — `"open"` (baseline, unrestricted) or `"premium"` (licensed). A
  bundled premium sample profile, `ACME_Premium` (`tier: premium`), ships to
  demonstrate the gate.
  - `list_profiles` now reports each profile's `tier` and a per-caller
    `entitled` boolean.
  - `get_profile` and `lint_payload` on a **premium** profile return a
    `BP_NOT_ENTITLED` error unless the caller is entitled; open profiles are
    always accessible.
  - Entitlement is granted by **either** an OAuth scope on the token
    (`profile:premium` grants every premium profile; `profile:<profile_id>`
    grants one) under the HTTP transport, **or** the
    `ISO20022_BANK_PROFILE_ENTITLEMENTS` environment allowlist
    (comma-/space-separated premium `profile_id` values; `*` grants all) under
    stdio / dev mode. The two sources are ORed.

### Documentation

- New [`docs/transport.md`](https://github.com/sebastienrousseau/iso20022-bank-profile-mcp/blob/main/docs/transport.md)
  covering the HTTP transport and OAuth 2.1 setup.
- [`docs/profiles.md`](https://github.com/sebastienrousseau/iso20022-bank-profile-mcp/blob/main/docs/profiles.md)
  gains an **Entitlement & premium packs** section; the README documents the
  HTTP transport and the concrete entitlement mechanism.

## [0.0.1] - 2026-07-18

Initial release: the bank clearing-profile Model Context Protocol (MCP) server
of the **ISO 20022 MCP Suite** — a fully local, closed-world server that
manages, validates, and serves the bank-specific clearing profiles / rule packs
that sit beyond structural XSD validation. It is a sibling of
`iso20022-readiness-suite-mcp`, which can consume the profiles this server
serves, ahead of the November 2026 ISO 20022 milestones.

### Added

- **4 MCP tools over stdio**, each a pure, local, read-only, idempotent,
  closed-world lookup that returns typed, JSON-serialisable data and an
  `{"error": ...}` payload on any failure (never a traceback):
  - `list_profiles` — list the available clearing profiles as lightweight
    summaries (`profile_id`, `market_practice`, `supported_messages`,
    `rule_count`).
  - `get_profile` — return one clearing profile in full, including its rule
    bodies.
  - `lint_payload` — evaluate a raw payload against a profile and return
    findings.
  - `validate_profile_definition` — validate a bank-supplied profile /
    rule-pack definition (raw JSON).
- **Clearing-profile engine**: bundled JSON baseline profiles (`Generic`,
  `CBPR+`, `SEPA_Instant`, `FedNow`) — open source — with a `register()` seam
  for runtime-loaded premium rule packs. The rule mini-language supports
  `required`, `equals:<v>`, and `if:<elem>=<v>:equals:<v2>` assertions; XML is
  parsed with `defusedxml` only.
- **`iso20022-bank-profile-mcp` console entry point** launching the FastMCP
  server over stdio (`--version` supported).
- **Read-only / closed-world tool annotations**: every tool is marked
  read-only, non-destructive, idempotent, and closed-world (no network, no
  sub-servers).
- **Supply chain**: 100% line + branch coverage gate, ruff + black +
  mypy `--strict` + bandit + interrogate in CI across Python 3.10/3.11/3.12/
  3.13; OpenSSF Scorecard; SLSA Build L3 provenance + PEP 740 sigstore
  attestations on release; CycloneDX 1.6 + SPDX 2.3 + pip-licenses SBOMs on
  every GitHub release; NIST SP 800-218 SSDF practice mapping in
  `SECURITY.md`; MCP registry + Glama directory manifests.

[0.0.2]: https://github.com/sebastienrousseau/iso20022-bank-profile-mcp/releases/tag/v0.0.2
[0.0.1]: https://github.com/sebastienrousseau/iso20022-bank-profile-mcp/releases/tag/v0.0.1
