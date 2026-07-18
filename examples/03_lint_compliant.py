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

"""Example: linting a CBPR+-compliant payload.

A pain.001 whose creditor address is fully structured (Ctry + TwnNm both
present) lints clean against CBPR+. Fully local.

Usage::

    python examples/03_lint_compliant.py
"""

from iso20022_bank_profile_mcp.server import lint_payload

_COMPLIANT = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
    "<CstmrCdtTrfInitn><PmtInf><Cdtr><PstlAdr>"
    "<StrtNm>Main St</StrtNm><TwnNm>London</TwnNm><Ctry>GB</Ctry>"
    "</PstlAdr></Cdtr></PmtInf></CstmrCdtTrfInitn></Document>"
)


def main() -> None:
    """Lint a compliant payload against CBPR+ and report the clean result."""
    result = lint_payload(_COMPLIANT, "CBPR+")
    print(f"Profile:     {result['profile_id']}")
    print(f"Compliant:   {result['is_compliant']}")
    print(f"Findings:    {len(result['findings'])}")


if __name__ == "__main__":
    main()
