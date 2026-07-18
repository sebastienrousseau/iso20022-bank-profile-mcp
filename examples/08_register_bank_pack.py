#!/usr/bin/env python3
# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Example: registering a bank-specific rule pack at runtime.

Validates a bank's rule pack from raw JSON, registers it on a live engine,
and lints a payload against the freshly-registered profile -- the pattern a
bank uses to bring its own market practice online. Fully local.

Usage::

    python examples/08_register_bank_pack.py
"""

from iso20022_bank_profile_mcp.engine import ProfileEngine

_DEFINITION = (
    '{"profile_id": "AcmeBank", "market_practice": "Acme house rules", '
    '"supported_messages": ["pacs.008"], '
    '"custom_rules": [{"rule_id": "acme-ccy-eur", '
    '"description": "Ccy must be EUR", "locator": "Ccy", '
    '"assertion": "equals:EUR", "error_code": "ACME_CCY_NOT_EUR"}]}'
)
_USD_PAYLOAD = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
    "<CstmrCdtTrfInitn><PmtInf><Ccy>USD</Ccy></PmtInf>"
    "</CstmrCdtTrfInitn></Document>"
)


def main() -> None:
    """Validate, register, then lint against a bank-specific rule pack."""
    engine = ProfileEngine.from_bundled()
    before = len(engine.list_profiles())

    profile = engine.validate_definition(_DEFINITION)
    engine.register(profile)
    print(
        f"Registered {profile.profile_id!r}: "
        f"{before} -> {len(engine.list_profiles())} profiles"
    )

    findings = engine.apply("AcmeBank", _USD_PAYLOAD)
    print(f"USD payload against AcmeBank -> {len(findings)} finding(s):")
    for finding in findings:
        print(f"  {finding.code} at {finding.locator}: {finding.explanation}")


if __name__ == "__main__":
    main()
