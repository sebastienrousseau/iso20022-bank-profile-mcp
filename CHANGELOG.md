# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.0.1]: https://github.com/sebastienrousseau/iso20022-bank-profile-mcp/releases/tag/v0.0.1
