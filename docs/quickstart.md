# Quickstart

A 10-minute install → MCP client config → first conversation tutorial
for `iso20022-bank-profile-mcp`, the bank clearing-profile server of the
ISO 20022 MCP Suite.

## 1. Install

`iso20022-bank-profile-mcp` runs on macOS, Linux, and Windows and
requires Python 3.10+. It pulls in the MCP SDK, `pydantic`, and
`defusedxml` automatically.

```sh
python -m pip install iso20022-bank-profile-mcp
```

Verify:

```sh
python -c "import iso20022_bank_profile_mcp; print(iso20022_bank_profile_mcp.__version__)"
```

The server is fully local and closed-world: every tool computes from the
bundled clearing-profile data, with no network calls and no sub-servers to
install.

## 2. Launch the server

The package installs an `iso20022-bank-profile-mcp` console entry
point that starts the server over stdio (FastMCP's default transport):

```sh
iso20022-bank-profile-mcp
```

The command speaks MCP on stdin/stdout — it is meant to be launched by
an MCP client, not used interactively. (`iso20022-bank-profile-mcp
--version` prints the version and exits.)

## 3. Register it with your MCP client

### Claude Desktop

Add an entry to `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "iso20022-bank-profile": { "command": "iso20022-bank-profile-mcp" }
  }
}
```

Restart Claude Desktop. The 4 tools are now available in any chat.

### Other clients (Cursor, Continue, generic stdio MCP clients)

Point the client at the `iso20022-bank-profile-mcp` command. The
server speaks standard MCP — no custom transport, no auth. If the entry
point is not on the client's `PATH` (GUI apps often have a minimal
`PATH`), use the absolute path from `which iso20022-bank-profile-mcp`
in the `command` field.

## 4. First conversation

Ask the agent to discover the profiles and lint a payload against one:

> Which clearing profiles are available? Take this pacs.008 message and
> lint it against the CBPR+ profile — tell me which market-practice rules
> it violates and why.

A typical flow: the agent calls `list_profiles` to discover the target
profiles, `get_profile` to inspect a profile's rule bodies, and
`lint_payload` to evaluate the payload against a profile and report the
findings. To vet a bank-supplied rule pack, it calls
`validate_profile_definition` with the candidate JSON.

## 5. Use in-process (no MCP client needed)

To prototype or write integration tests, call the tools through the
FastMCP instance directly. Everything is local:

```python
import asyncio

from iso20022_bank_profile_mcp import server


async def main() -> None:
    result = await server.server.call_tool("list_profiles", {})
    content = result[0] if isinstance(result, tuple) else result
    print(content[0].text)  # -> {"profile_id": "...", "rule_count": ...}


asyncio.run(main())
```

## 6. The 4 tools at a glance

| Tool | What it does |
| --- | --- |
| `list_profiles` | List the clearing profiles (Generic, CBPR+, SEPA_Instant, FedNow) as lightweight summaries |
| `get_profile` | Return one clearing profile in full, including its rule bodies |
| `lint_payload` | Evaluate a raw payload against a profile and return findings |
| `validate_profile_definition` | Validate a bank-supplied profile / rule-pack definition (raw JSON) |

Every tool is read-only, idempotent, and closed-world (no network, no
sub-servers).

## 7. Next steps

- Read [`profiles.md`](profiles.md) for the clearing profiles, the rule
  mini-language, and how premium rule packs plug in.
- Browse the full [tool catalog](https://github.com/sebastienrousseau/iso20022-bank-profile-mcp/blob/main/README.md#tools).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `command not found: iso20022-bank-profile-mcp` | Install went to a venv that isn't on PATH | Re-install in your active env, or invoke `python -m iso20022_bank_profile_mcp.server` |
| MCP client doesn't see the tools | Wrong path in client config | Use an absolute path: `which iso20022-bank-profile-mcp` → paste into the client `command` |
| `get_profile` returns an `{"error": ...}` | Unknown `profile_id` | Call `list_profiles` first and pass one of the returned `profile_id` values |
| `lint_payload` reports an XML parse error | The `payload_content` was not well-formed XML | Pass the raw message text (not a path); the engine parses it with `defusedxml` |
