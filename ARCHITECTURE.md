<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# iso20022-bank-profile-mcp Architecture

A map of the codebase for new contributors and maintainers. The goal is
that anyone can navigate, extend, and reason about
iso20022-bank-profile-mcp without prior context.

## The pipeline

```
MCP client (Claude Desktop, IDE, agent, gateway)
        |  stdio (JSON-RPC), streamable HTTP, SSE,
        |  or authenticated streamable HTTP (http/transport.py)
        v
iso20022_bank_profile_mcp/server.py   (FastMCP: tools, resources, prompt)
        |  entitlement gate, errors as data
        v
iso20022_bank_profile_mcp/engine.py   (ProfileEngine: load, register,
        |                              validate a definition, apply rules)
        v
data/profiles/*.json                  (Generic, CBPR+, SEPA_Instant,
                                       FedNow, ACME_Premium sample)
```

The server is fully local and closed-world: every tool computes from the
bundled clearing-profile data (plus anything registered at runtime) and
returns typed, JSON-serialisable output. Nothing here parses, generates
or structurally validates ISO 20022 messages; that is the job of the
foundational suite servers. This server owns the market-practice layer
above the XSD.

## Module map

| Area | Module | Responsibility |
| :--- | :--- | :--- |
| **Server** | `iso20022_bank_profile_mcp/server.py` | The FastMCP instance, the 4 tools, 2 resources and 1 prompt, the entitlement gate around premium profiles, the argparse `main()` |
| **Entry point** | `iso20022_bank_profile_mcp.server:main` (console script: `iso20022-bank-profile-mcp`) | Launches the server over stdio, over streamable HTTP / SSE with `--transport` (`_cli.py`, `_transports.py`, ADR 0001), or over authenticated streamable HTTP with `--transport http --bind` (`http/transport.py`) |
| **Suite command line** | `iso20022_bank_profile_mcp/_cli.py`, `iso20022_bank_profile_mcp/_transports.py` | `--host`/`--port` and the transport dispatch, copied verbatim into every server of the suite; work on mcp 1.x and 2.x |
| **Engine** | `iso20022_bank_profile_mcp/engine.py` | `ProfileEngine`: loads the bundled profiles, `register()` for runtime rule packs, validates a definition, applies a profile's rules to a payload (`defusedxml` only) |
| **Models** | `iso20022_bank_profile_mcp/models.py` | Pydantic models: `ClearingProfile`, `ProfileRule`, `ProfileSummary`, the tool request / response shapes |
| **Errors** | `iso20022_bank_profile_mcp/errors.py` | `BankProfileError` and its subclasses, each rendering to an `ErrorDetail` (`code`, `explanation`, `locator`) |
| **Entitlement** | `iso20022_bank_profile_mcp/entitlement.py` | Whether a caller may use a premium profile: an OAuth scope (`profile:premium`, `profile:<id>`) or the `ISO20022_BANK_PROFILE_ENTITLEMENTS` allowlist |
| **Authenticated HTTP** | `iso20022_bank_profile_mcp/http/transport.py` | Streamable HTTP that refuses to start without auth: OAuth 2.1 resource server or the static `ISO20022_BANK_PROFILE_TOKEN` dev-mode token |
| **OAuth** | `iso20022_bank_profile_mcp/http/oauth.py` | OAuth 2.1 resource-server JWT validation (RFC 9728): JWKS cache, `iss` / `aud` / `exp` / `nbf` / scope checks, protected-resource metadata |
| **Request context** | `iso20022_bank_profile_mcp/http/context.py` | The tenant (`X-MCP-Tenant`) and scopes of the current request, as context variables the tools read |
| **Tracing** | `iso20022_bank_profile_mcp/tracing.py` | Opt-in OpenTelemetry tracing behind the `[otel]` extra (`--otel-endpoint`) |
| **SDK shim** | `iso20022_bank_profile_mcp/_mcp_compat.py` | One import surface over mcp 1.x (`FastMCP`) and 2.x (`MCPServer`) |
| **Profiles** | `iso20022_bank_profile_mcp/data/profiles/*.json` | The bundled clearing profiles: `Generic`, `CBPR+`, `SEPA_Instant`, `FedNow` (open) and the `ACME_Premium` sample pack that demonstrates the gate |
| **Version** | `iso20022_bank_profile_mcp/__init__.py` | Single source of truth (`__version__`) |
| **Tests** | `tests/` | In-process regressions per module, the HTTP transport and OAuth tests, the README / docs snippet runner, the suite conformance invariants |
| **Benchmarks** | `benches/bench_lint_payload.py` | What linting costs and how it grows with the payload; CI runs `--quick` |
| **Examples** | `examples/` | One runnable script per usage shape, executed by a test |
| **Release helpers** | `scripts/verify_versions.py`, `scripts/check_suite_consistency.py` | Version sources agree; the tree agrees with what PyPI publishes |

## Tools, resources, prompt

The current MCP surface:

- **Tools** (4), every one a pure, local, read-only, idempotent,
  closed-world lookup: `list_profiles`, `get_profile`, `lint_payload`,
  `validate_profile_definition`.
- **Resources** (2): `bankprofile://profiles` and the templated
  `bankprofile://profile/{profile_id}`.
- **Prompt** (1): `lint_bank_payload`.

## Key design decisions

- **Profiles are data.** A clearing profile is a `profile_id`, its
  `market_practice`, the messages it supports and a list of declarative
  `custom_rules` in a small assertion language (`required`,
  `equals:<v>`, `if:<elem>=<v>:equals:<v2>`). Adding a scheme means
  adding a JSON file, not code.
- **Errors as data.** Tools do not raise on bad input. A
  `BankProfileError` or a bad argument becomes an `{"error": ...}`
  payload so the agent can reason about failure without parsing
  tracebacks.
- **The gate refuses before doing the work.** A premium profile the
  caller is not entitled to returns `BP_NOT_ENTITLED` before any rule
  is evaluated, so the refusal leaks no timing about rules the caller
  may not see.
- **Four transports, one command line.** stdio for a client that spawns
  the process; streamable HTTP and SSE from the suite's shared
  `_cli`/`_transports` pair, unauthenticated and bound to loopback by
  default; authenticated streamable HTTP in `http/transport.py` for
  shared multi-tenant deployments (ADR 0001).
- **Closed world.** No network calls from any tool, no sub-servers, XML
  parsed with `defusedxml` only.
- **Optional extras stay optional.** OpenTelemetry (`[otel]`) is
  imported lazily; without it tracing is a no-op.
- **Coverage enforced at 100%** line+branch and docstring
  (`interrogate`); the suite-conformance test pins the invariants every
  repository of the suite shares.

## Extension points

- **Add a profile:** a JSON file in
  `iso20022_bank_profile_mcp/data/profiles/`; the engine picks it up
  from `from_bundled()`. Pair it with a fixture and a test in
  `tests/test_engine.py`, and document it in `docs/profiles.md`.
- **Add a rule assertion:** extend `ProfileEngine._evaluate` and
  `_assertion_is_known` together, so `validate_profile_definition`
  accepts exactly what `lint_payload` can evaluate.
- **Add a tool:** a `@server.tool(...)` function in
  `iso20022_bank_profile_mcp/server.py`; pair it with tests in
  `tests/test_server.py`, document it in the README and update the tool
  count in `glama.json` and `server.json`.
- **Load a bank's own pack at runtime:** `ProfileEngine.register()`
  (see `examples/08_register_bank_pack.py`).

## Where to look first

- Runnable examples: [`examples/`](examples/)
- Decisions: [`docs/adr/`](docs/adr/index.md)
- Roadmap: [`ROADMAP.md`](ROADMAP.md)
- Release process: [`RELEASING.md`](RELEASING.md)
- The profiles: [`docs/profiles.md`](docs/profiles.md)
