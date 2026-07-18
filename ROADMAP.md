<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# `iso20022-bank-profile-mcp` roadmap

## Mission

The bank clearing-profile Model Context Protocol (MCP) server for the
**ISO 20022 MCP Suite**. It manages, validates, and serves the bank-specific
clearing profiles / rule packs — the market-practice rules that sit beyond
structural XSD validation. It is a fully local, closed-world server and a
sibling of `iso20022-readiness-suite-mcp`, which can consume the profiles this
server serves, ahead of the November 2026 ISO 20022 milestones.

## Where we are (v0.0.1, shipped 2026-07-18)

- **4 MCP tools** over stdio, each a pure, local, read-only, idempotent,
  closed-world lookup that returns typed, JSON-serialisable data and an
  `{"error": ...}` payload on any failure (never a traceback):
  - Discovery: `list_profiles` — list the available clearing profiles as
    lightweight summaries (`profile_id`, `market_practice`,
    `supported_messages`, `rule_count`).
  - Retrieval: `get_profile` — return one clearing profile in full,
    including its rule bodies.
  - Linting: `lint_payload` — evaluate a raw payload against a profile and
    return findings.
  - Validation: `validate_profile_definition` — validate a bank-supplied
    profile / rule-pack definition (raw JSON).
- **Clearing-profile engine**: bundled JSON baseline profiles (`Generic`,
  `CBPR+`, `SEPA_Instant`, `FedNow`) — open source — with a `register()` seam
  for runtime-loaded premium rule packs. The rule mini-language supports
  `required`, `equals:<v>`, and `if:<elem>=<v>:equals:<v2>` assertions.
- **Stdio transport** (FastMCP default): one process per operator, launched
  by the MCP client, no network surface, no authentication needed. XML is
  parsed with `defusedxml` only.
- **Supply chain**: 100% line + branch coverage, OpenSSF Scorecard, SLSA
  Build L3 + PEP 740 sigstore attestations on every release, CycloneDX 1.6 +
  SPDX 2.3 + pip-licenses SBOMs on every GitHub release, NIST SP 800-218 SSDF
  practice mapping in `SECURITY.md`.

## Delivered since (v0.0.2, shipped 2026-07-18)

- **Optional streamable-HTTP transport** with OAuth 2.1 resource-server auth:
  `iso20022-bank-profile-mcp --transport=http --bind=HOST:PORT` alongside the
  default stdio. OAuth 2.1 (RFC 9728) validates bearer JWTs when the
  `ISO20022_BANK_PROFILE_OAUTH_*` variables are set (a static dev-mode token is
  the fallback; starting HTTP with no auth is refused), and an optional
  `X-MCP-Tenant` header is forwarded into the request context for multi-tenant
  scoping.
- **Premium rule-pack entitlement gating**: profiles carry a `tier`
  (`open` / `premium`), `list_profiles` exposes `tier` + a per-caller
  `entitled` flag, and `get_profile` / `lint_payload` return `BP_NOT_ENTITLED`
  on a premium profile unless the caller is entitled via an OAuth scope
  (`profile:premium` / `profile:<id>`) or the
  `ISO20022_BANK_PROFILE_ENTITLEMENTS` allowlist. A bundled `ACME_Premium`
  sample pack demonstrates the gate.

## Fast-follow — richer rule packs

Goal: broaden the profile catalogue.

- **Richer bank rule packs**: more scheme profiles (HVPS+, T2, additional
  domestic instant schemes) and a wider rule mini-language (cardinality,
  regex, cross-field assertions) so a profile can capture more of a bank's
  market practice. The `iso20022-readiness-suite-mcp` gateway consumes
  whatever profiles this server serves.

## Later

Goal: post-Nov-2026, field-tested behaviour.

- **Observability**: Prometheus metrics on the MCP layer (request/tool
  counters, tool latency histograms) and a tamper-evident audit chain over
  profile reads and lint runs.
- **Profile authoring tooling**: a linting/diff surface for authored rule
  packs so bank teams can evolve their profiles safely.
- **MCP API surface freeze** at the first stable minor: any future tool name
  change becomes a minor-bump event per SemVer.
- **OpenSSF Best Practices** badge progression (Passing → Silver → Gold).

## Out of scope (until a contributor steps up)

- **Embedded LLM**: this server delegates all inference to the client's model
  via MCP; no bundled LLM weights, no hosted inference endpoint.
- **OAuth provider integration**: the HTTP transport authenticates by
  validating tokens from your existing authorization server (Okta, Auth0,
  Entra ID, ...); running the authorization server is the operator's job.
- **Structural XSD validation / message generation**: parsing, generation, and
  low-level structural validation stay in the foundational suite servers; this
  server owns only the market-practice profile layer on top of them.

## How to influence the roadmap

- Open an issue with the proposed tool / profile + the use case it unblocks.
- For larger items, sketch a design in the issue body.
- See [`GOVERNANCE.md`](GOVERNANCE.md) for the decision-making process.
