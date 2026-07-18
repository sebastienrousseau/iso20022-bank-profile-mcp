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

"""Example: ``get_profile``.

Fetches one clearing profile in full, including its rule bodies, so you can
inspect exactly what each market practice asserts. Fully local.

Usage::

    python examples/02_get_profile.py
"""

from iso20022_bank_profile_mcp.server import get_profile


def main() -> None:
    """Print the CBPR+ profile and each of its custom rules."""
    profile = get_profile("CBPR+")
    print(f"Profile: {profile['profile_id']} ({profile['market_practice']})")
    print(f"Supported messages: {', '.join(profile['supported_messages'])}")
    print(f"Rules ({len(profile['custom_rules'])}):")
    for rule in profile["custom_rules"]:
        print(
            f"  {rule['rule_id']:<12} {rule['assertion']:<24} "
            f"-> {rule['error_code']}"
        )


if __name__ == "__main__":
    main()
