# iso20022-bank-profile-mcp documentation

`iso20022-bank-profile-mcp` is the **bank clearing-profile server** of the
ISO 20022 MCP Suite. It is a fully local, closed-world MCP server — no network
surface, no sub-servers — that manages, validates, and serves the bank-specific
clearing profiles / rule packs, the market-practice rules that sit *beyond*
structural XSD validation. It is a sibling of `iso20022-readiness-suite-mcp`,
which can consume the profiles this server serves. Every tool returns typed,
JSON-serialisable data on every path — never a traceback.

## Start here

- [Quick start](quickstart.md) — install, configure the server in an MCP
  client, and run your first profile lookup and payload lint.

## Reference

- [Clearing profiles](profiles.md) — the baseline profiles (`Generic`,
  `CBPR+`, `SEPA_Instant`, `FedNow`), the rule mini-language, and the
  premium rule-pack seam.

## The tools

| Tool | What it does |
| --- | --- |
| `list_profiles` | List the available clearing profiles as lightweight summaries. |
| `get_profile` | Return one clearing profile in full, including its rule bodies. |
| `lint_payload` | Evaluate a raw payload against a profile and return findings. |
| `validate_profile_definition` | Validate a bank-supplied profile / rule-pack definition (raw JSON). |

Every tool is a pure, local, read-only, idempotent, closed-world lookup.

## Part of the ISO 20022 MCP Suite

This server owns the market-practice profile layer of the suite. The sibling
`iso20022-readiness-suite-mcp` gateway composes the foundational servers
(`iso20022-mcp`, `camt053-mcp`, `pain001-mcp`, `reconcile-mcp`,
`bankstatementparser-mcp`, `structured-address-fix-mcp`) and can consume the
profiles this server serves. See the
[project README](https://github.com/sebastienrousseau/iso20022-bank-profile-mcp)
for the full suite map.
