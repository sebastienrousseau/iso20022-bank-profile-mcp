# Clearing profiles

A **clearing profile** captures the market-practice assertions that lie
*beyond* structural XSD validation — the scheme-specific rules a payment
must satisfy to clear. `iso20022-bank-profile-mcp` ships a small set of
open baseline profiles and lets premium, bank-specific rule packs plug in
at runtime through the same engine.

Discover the profiles an installation offers with the `list_profiles`
tool, fetch one in full with `get_profile`, and evaluate a payload
against one with `lint_payload`. To vet a candidate rule pack before it
is served, run `validate_profile_definition` over its raw JSON.

## The bundled (open-source) profiles

| `profile_id` | Market practice | Supported messages | Baseline rules |
| --- | --- | --- | --- |
| `Generic` | ISO 20022 baseline | (none) | No market-practice assertions — the structural baseline. |
| `CBPR+` | SWIFT CBPR+ UG2026 | pacs.008, pacs.009, pain.001 | Every postal address must carry a `Ctry` (country) and a `TwnNm` (town) element from the Nov 2026 cliff. |
| `SEPA_Instant` | SEPA SCT Inst | pacs.008, pain.001 | For EUR payments the charge bearer (`ChrgBr`) must be `SLEV`. |
| `FedNow` | FedNow Core | pacs.008, pacs.002 | FedNow requires a structured `Ctry` element on party addresses. |

`Generic` is intentionally empty: it carries no extra market-practice
assertions, so a payload always lints clean against it. It is the neutral
baseline to compare the scheme profiles against.

## How a profile is evaluated

Profiles are **pure data** — bundled JSON for the open baseline, loadable
at runtime for premium packs. The `ProfileEngine` loads them, then
evaluates each rule against a payload parsed with `defusedxml` only.

Each rule is a small declarative assertion:

| Assertion form | Meaning |
| --- | --- |
| `required` | The `locator` element must be present somewhere in the payload. |
| `equals:<value>` | The `locator` element's text must equal `<value>`. |
| `if:<elem>=<val>:equals:<val2>` | Conditional: only when `<elem>` equals `<val>`, the `locator` element's text must equal `<val2>`. |

A rule that is violated produces a finding — a typed `ErrorDetail`
carrying its `error_code`, a human-readable explanation, and the rule's
`severity` (`info` / `warning` / `error`). `lint_payload` folds those
findings into its response; a compliant payload yields no findings and
`is_compliant` is `true`.

A bundled profile is just a JSON document, e.g. the SEPA Instant EUR
charge-bearer rule:

```json
{
  "profile_id": "SEPA_Instant",
  "market_practice": "SEPA SCT Inst",
  "supported_messages": ["pacs.008", "pain.001"],
  "custom_rules": [
    {
      "rule_id": "sepa-eur-slev",
      "description": "For EUR payments the charge bearer (ChrgBr) must be SLEV.",
      "locator": "ChrgBr",
      "assertion": "if:Ccy=EUR:equals:SLEV",
      "error_code": "SEPA_CHRGBR_NOT_SLEV",
      "severity": "error"
    }
  ]
}
```

The `validate_profile_definition` tool accepts exactly this shape as raw
JSON text and confirms that every rule's `assertion` uses a known verb
(`required`, `equals:`, or `if:`) before a profile is served.

## How premium rule packs plug in

The engine exposes two seams:

- `ProfileEngine.from_bundled()` loads the open baseline profiles that
  ship inside the package (`data/profiles/*.json`). This is what the
  shipped console script uses.
- `ProfileEngine.register(profile)` registers (or replaces) a profile at
  runtime — the extension point for **premium, institution-specific rule
  packs**.

A premium pack is the *same shape* as a bundled profile: a
`ClearingProfile` with a `profile_id`, a `market_practice`, its
`supported_messages`, and a list of `custom_rules`. A deployment that
embeds the server can build an engine, register its licensed packs, and
serve them alongside the open baseline:

```python
from iso20022_bank_profile_mcp.engine import ProfileEngine
from iso20022_bank_profile_mcp.models import ClearingProfile

engine = ProfileEngine.from_bundled()      # open baseline

bank_pack = {
    "profile_id": "AcmeBank",
    "market_practice": "Acme house rules",
    "tier": "premium",
    "supported_messages": ["pacs.008"],
    "custom_rules": [
        {
            "rule_id": "acme-ccy-eur",
            "description": "Settlement currency must be EUR.",
            "locator": "Ccy",
            "assertion": "equals:EUR",
            "error_code": "ACME_CCY_NOT_EUR",
        }
    ],
}
engine.register(                           # premium / bank-specific pack
    ClearingProfile.model_validate(bank_pack)
)
print([p.profile_id for p in engine.list_profiles()])
```

Once registered, a pack's `profile_id` appears in `list_profiles` and is
accepted by `get_profile` and `lint_payload` — the tool surface does not
change.

The sibling `iso20022-readiness-suite-mcp` gateway consumes whatever
profiles this server serves. Everything in the open-source tier — the
bundled open profiles and the engine itself — is unrestricted and not
feature-gated.

## Entitlement & premium packs

Every profile carries a **`tier`**: `"open"` (the baseline profiles —
unrestricted and always accessible) or `"premium"` (a licensed rule pack).
A bundled premium **sample** profile, `ACME_Premium` (`tier: premium`),
ships so the gate can be exercised without a real licensed pack.

- `list_profiles` reports each profile's `tier` and a per-caller
  **`entitled`** boolean, so a client can see which packs the current
  caller may use before calling anything else.
- `get_profile` and `lint_payload` on a **premium** profile return a
  `BP_NOT_ENTITLED` error unless the caller is entitled. Open profiles are
  always accessible.

Entitlement is resolved from two independent sources so the same server
works under both transports; **either** one grants access (they are ORed):

| Source | Transport | How to grant |
| --- | --- | --- |
| **OAuth scope** | HTTP | A token bearing `profile:premium` is entitled to *every* premium profile; a token bearing `profile:<profile_id>` is entitled to just that one. |
| **Environment allowlist** | stdio / dev | `ISO20022_BANK_PROFILE_ENTITLEMENTS` lists the premium `profile_id` values (comma- or space-separated) the operator is licensed for; `*` grants all. |

Under stdio, for example, licensing the `ACME_Premium` sample pack for one
process is just:

```sh
ISO20022_BANK_PROFILE_ENTITLEMENTS=ACME_Premium iso20022-bank-profile-mcp
```

Under the HTTP transport the caller's OAuth token carries the granting
scope instead — see [HTTP transport & authentication](transport.md).
The open-source tier — the bundled open profiles and the engine itself —
is never gated; only `premium`-tier profiles require an entitlement.

## Choosing a profile

- **Cross-border / correspondent banking:** `CBPR+`.
- **Euro instant payments:** `SEPA_Instant`.
- **US instant payments:** `FedNow`.
- **No scheme rules, structural baseline only:** `Generic`.

When in doubt, call `list_profiles` first to see exactly what an
installation offers, then `lint_payload` against each candidate profile
and compare the findings.
