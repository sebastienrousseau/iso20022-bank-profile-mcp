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

"""Example: premium rule-pack entitlement gating.

Premium profiles (``tier == "premium"``, e.g. the bundled ``ACME_Premium``)
are gated: ``get_profile`` / ``lint_payload`` return ``BP_NOT_ENTITLED``
unless the caller is entitled. Entitlement is granted by an OAuth scope
(``profile:premium``) under the HTTP transport, OR by the
``ISO20022_BANK_PROFILE_ENTITLEMENTS`` env allowlist under stdio. This example
demonstrates both grant paths, fully local.

Usage::

    python examples/09_premium_entitlement.py
"""

import os

from iso20022_bank_profile_mcp import server
from iso20022_bank_profile_mcp.http.context import _scopes_var

_PAYLOAD = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">'
    "<Ccy>USD</Ccy></Document>"
)


def main() -> None:
    """Show a premium profile gated, then unlocked two ways."""
    summaries = {p["profile_id"]: p for p in server.list_profiles()}
    acme = summaries["ACME_Premium"]
    print(
        f"ACME_Premium: tier={acme['tier']} "
        f"entitled(default stdio)={acme['entitled']}"
    )

    # 1. No entitlement -> gated.
    denied = server.get_profile("ACME_Premium")
    print(f"get_profile (no entitlement) -> {denied['error']['code']}")

    # 2. Grant via the environment allowlist (stdio / dev).
    os.environ["ISO20022_BANK_PROFILE_ENTITLEMENTS"] = "ACME_Premium"
    try:
        granted = server.get_profile("ACME_Premium")
        lint = server.lint_payload(_PAYLOAD, "ACME_Premium")
        print(
            f"get_profile (env allowlist) -> ok, "
            f"{len(granted['custom_rules'])} rules; "
            f"lint -> {len(lint['findings'])} finding(s)"
        )
    finally:
        del os.environ["ISO20022_BANK_PROFILE_ENTITLEMENTS"]

    # 3. Grant via an OAuth scope (as the HTTP transport would set it).
    token = _scopes_var.set(("profile:premium",))
    try:
        scoped = server.get_profile("ACME_Premium")
        print(
            "get_profile (OAuth scope 'profile:premium') -> "
            f"{'ok' if 'profile_id' in scoped else scoped}"
        )
    finally:
        _scopes_var.reset(token)


if __name__ == "__main__":
    main()
