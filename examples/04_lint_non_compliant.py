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

"""Example: linting a non-compliant CBPR+ payload.

A pain.001 whose creditor postal address omits both Ctry and TwnNm raises
the two CBPR+ findings that the Nov 2026 cliff will reject. Fully local.

Usage::

    python examples/04_lint_non_compliant.py
"""

from iso20022_bank_profile_mcp.server import lint_payload

_NON_COMPLIANT = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
    "<CstmrCdtTrfInitn><PmtInf><Cdtr>"
    "<PstlAdr><StrtNm>Main St</StrtNm></PstlAdr>"
    "</Cdtr></PmtInf></CstmrCdtTrfInitn></Document>"
)


def main() -> None:
    """Lint a non-compliant payload and print each CBPR+ finding raised."""
    result = lint_payload(_NON_COMPLIANT, "CBPR+")
    print(f"Profile:   {result['profile_id']}")
    print(f"Compliant: {result['is_compliant']}")
    print(f"CBPR+ raised {len(result['findings'])} finding(s):")
    for finding in result["findings"]:
        severity = finding["context"].get("severity", "error")
        print(
            f"  [{severity}] {finding['code']} at {finding['locator']}: "
            f"{finding['explanation']}"
        )


if __name__ == "__main__":
    main()
