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

"""Premium rule-pack entitlement gating.

Baseline (``tier == "open"``) profiles are unrestricted. A ``"premium"``
profile is licensed and requires an entitlement, resolved from two independent
sources so the same server works under both transports:

* **OAuth scope** (HTTP transport) -- a token bearing the :data:`PREMIUM_SCOPE`
  (``profile:premium``) is entitled to every premium profile; a token bearing
  the profile-specific scope ``profile:<profile_id>`` is entitled to just that
  one.
* **Environment allowlist** (stdio / dev) -- the
  ``ISO20022_BANK_PROFILE_ENTITLEMENTS`` variable lists the premium
  ``profile_id`` values (comma- or space-separated) the operator is licensed
  for; ``*`` grants all of them.

The two are ORed: either grants access. This module is pure — the caller
supplies the scopes and the allowlist — so it is trivially testable and never
reads global state itself.
"""

from __future__ import annotations

import os
from collections.abc import Collection, Mapping, Sequence

#: The OAuth scope granting access to every premium profile.
PREMIUM_SCOPE = "profile:premium"

#: The environment variable listing entitled premium ``profile_id`` values.
ENTITLEMENTS_ENV = "ISO20022_BANK_PROFILE_ENTITLEMENTS"


def allowlist_from_env(
    environ: Mapping[str, str] | None = None,
) -> frozenset[str]:
    """Parse the entitled-profile allowlist from the environment.

    Args:
        environ: The environment mapping to read; ``None`` uses ``os.environ``.

    Returns:
        The set of entitled premium ``profile_id`` values (``{"*"}`` grants
        all), or an empty set when the variable is unset/empty.
    """
    env = os.environ if environ is None else environ
    raw = env.get(ENTITLEMENTS_ENV, "")
    return frozenset(raw.replace(",", " ").split())


def is_entitled(
    profile_id: str,
    tier: str,
    scopes: Sequence[str],
    allowlist: Collection[str],
) -> bool:
    """Return whether a caller may use ``profile_id``.

    Open-tier profiles are always permitted. A premium profile requires either
    a granting OAuth scope (:data:`PREMIUM_SCOPE` or ``profile:<profile_id>``)
    or membership of the environment ``allowlist`` (``"*"`` grants all).

    Args:
        profile_id: The profile being accessed.
        tier: The profile's tier (``"open"`` or ``"premium"``).
        scopes: The current caller's OAuth scopes (empty under stdio).
        allowlist: The entitled-profile allowlist (see
            :func:`allowlist_from_env`).

    Returns:
        ``True`` when access is permitted, ``False`` otherwise.
    """
    if tier != "premium":
        return True
    if PREMIUM_SCOPE in scopes or f"profile:{profile_id}" in scopes:
        return True
    return "*" in allowlist or profile_id in allowlist
