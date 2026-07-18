# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
