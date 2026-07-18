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

"""Example: validating a good rule-pack definition.

A bank ships a rule pack as raw JSON. ``validate_profile_definition``
confirms it fits the schema and uses only assertion verbs the engine can
evaluate. Fully local.

Usage::

    python examples/05_validate_good_definition.py
"""

from iso20022_bank_profile_mcp.server import validate_profile_definition

_DEFINITION = (
    '{"profile_id": "AcmeBank", '
    '"market_practice": "Acme house rules", '
    '"supported_messages": ["pacs.008"], '
    '"custom_rules": ['
    '{"rule_id": "acme-ctry", "description": "Ctry is required", '
    '"locator": "Ctry", "assertion": "required", '
    '"error_code": "ACME_MISSING_CTRY"}, '
    '{"rule_id": "acme-eur-slev", '
    '"description": "EUR payments must use SLEV", '
    '"locator": "ChrgBr", "assertion": "if:Ccy=EUR:equals:SLEV", '
    '"error_code": "ACME_CHRGBR_NOT_SLEV"}]}'
)


def main() -> None:
    """Validate a well-formed rule pack and report the outcome."""
    result = validate_profile_definition(_DEFINITION)
    print(f"Valid:      {result['is_valid']}")
    print(f"Profile id: {result['profile_id']}")
    print(f"Rule count: {result['rule_count']}")


if __name__ == "__main__":
    main()
