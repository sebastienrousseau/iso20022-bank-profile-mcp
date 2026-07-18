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

"""Example: rejecting a bad rule-pack definition.

A rule pack that references an assertion verb the engine cannot evaluate
(``frobnicate``) is rejected as data -- ``is_valid`` is False and the error
detail locates the offending rule. Fully local.

Usage::

    python examples/06_validate_bad_definition.py
"""

from iso20022_bank_profile_mcp.server import validate_profile_definition

_DEFINITION = (
    '{"profile_id": "BrokenBank", "market_practice": "typo edition", '
    '"custom_rules": [{"rule_id": "oops", '
    '"description": "unknown verb", "locator": "Ctry", '
    '"assertion": "frobnicate", "error_code": "OOPS"}]}'
)


def main() -> None:
    """Validate a broken rule pack and print why it was rejected."""
    result = validate_profile_definition(_DEFINITION)
    print(f"Valid: {result['is_valid']}")
    for err in result["errors"]:
        print(f"  {err['code']} at {err['locator']}: {err['explanation']}")


if __name__ == "__main__":
    main()
