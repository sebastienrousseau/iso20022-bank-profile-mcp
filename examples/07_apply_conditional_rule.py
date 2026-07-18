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

"""Example: applying ``equals:`` and ``if:`` rules with the engine.

Drives the :class:`ProfileEngine` directly to show the SEPA_Instant
conditional rule (``if:Ccy=EUR:equals:SLEV``) firing for a EUR payment with
the wrong charge bearer, and staying silent for a non-EUR payment. Fully
local.

Usage::

    python examples/07_apply_conditional_rule.py
"""

from iso20022_bank_profile_mcp.engine import ProfileEngine

_EUR_BAD = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
    "<CstmrCdtTrfInitn><PmtInf>"
    "<Ccy>EUR</Ccy><ChrgBr>DEBT</ChrgBr>"
    "</PmtInf></CstmrCdtTrfInitn></Document>"
)
_USD = _EUR_BAD.replace("EUR", "USD")


def main() -> None:
    """Apply the SEPA_Instant conditional rule to two payments."""
    engine = ProfileEngine.from_bundled()

    eur = engine.apply("SEPA_Instant", _EUR_BAD)
    print(f"EUR/DEBT payment -> {len(eur)} finding(s):")
    for finding in eur:
        print(f"  {finding.code} at {finding.locator}: {finding.explanation}")

    usd = engine.apply("SEPA_Instant", _USD)
    print(f"USD/DEBT payment -> {len(usd)} finding(s) (rule not applicable)")


if __name__ == "__main__":
    main()
