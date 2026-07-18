# iso20022-bank-profile-mcp examples

Runnable, self-contained examples for the ISO 20022 bank clearing-profile
MCP server. Each script drives the public tools or the `ProfileEngine`
directly. Every example is fully local and closed-world -- no network, no
sub-servers. Run any of them from the repository root:

```sh
python examples/<name>.py
```

| Example | Focus |
|---------|-------|
| [`01_list_profiles.py`](01_list_profiles.py) | Discover the clearing profiles (`profile_id` values) |
| [`02_get_profile.py`](02_get_profile.py) | Fetch one profile in full, including its rule bodies |
| [`03_lint_compliant.py`](03_lint_compliant.py) | Lint a CBPR+-compliant payload (no findings) |
| [`04_lint_non_compliant.py`](04_lint_non_compliant.py) | Lint a non-compliant payload (two CBPR+ findings) |
| [`05_validate_good_definition.py`](05_validate_good_definition.py) | Validate a well-formed rule-pack definition |
| [`06_validate_bad_definition.py`](06_validate_bad_definition.py) | Reject a rule pack that uses an unknown assertion verb |
| [`07_apply_conditional_rule.py`](07_apply_conditional_rule.py) | Apply `equals:` / `if:` rules via the engine |
| [`08_register_bank_pack.py`](08_register_bank_pack.py) | Validate and register a bank-specific rule pack, then lint |
| [`09_premium_entitlement.py`](09_premium_entitlement.py) | Premium-profile gating unlocked via an OAuth scope or the env allowlist |

## Installation

The examples import from `iso20022_bank_profile_mcp`, so install the package
first (Python 3.10+):

```sh
pip install iso20022-bank-profile-mcp
```

When running from a checkout without installing, put the repository root on
`PYTHONPATH`:

```sh
PYTHONPATH=. python examples/01_list_profiles.py
```
