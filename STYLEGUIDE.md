<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# `iso20022-bank-profile-mcp` style guide

`iso20022-bank-profile-mcp` follows the shared conventions of the
**ISO 20022 MCP Suite**. Those conventions are the single source of truth for:

- Voice + spelling conventions (British prose, American code, no em-dashes,
  no emojis outside the standard checkmark/cross in supported-versions
  tables).
- README structure (section template + badge order).
- CHANGELOG structure (Keep-a-Changelog + suite Quality gates).
- SECURITY.md structure (including the NIST SSDF practice mapping).
- SUPPORT.md / CONTRIBUTING.md structure.
- CI floor (test + lint + security + docstring-coverage gates + release-only
  gates).
- PR style (conventional commits + signed commits + branch policy).
- Branch naming, issue filing, naming conventions.

## Local additions

`iso20022-bank-profile-mcp` follows the suite convention that **MCP tool
names use the `verbNoun` snake_case pattern**:

```
list_profiles                 # not get_profiles or profiles()
get_profile                   # not profile() or fetch_profile
lint_payload                  # not payload_lint or check_payload
validate_profile_definition   # not profile_validate or is_valid_profile
```

This makes tool names read naturally as English imperatives in agent
prompts.

Two profile-server conventions:

- **Errors are data, not tracebacks.** Every tool returns an
  `{"error": ...}` payload on failure; a domain, validation, or value error
  is rendered as a typed `ErrorDetail` and never raised across the tool
  boundary.
- **Payloads are content, not paths.** Tools accept raw ISO 20022 message
  text (`payload_content`) and raw profile JSON (`definition_content`),
  never a server filesystem path.

## Updating

If you find divergence between this repo's practice and the shared suite
conventions, the suite wins; open a PR to align this repo (and/or fix the
deviation).
