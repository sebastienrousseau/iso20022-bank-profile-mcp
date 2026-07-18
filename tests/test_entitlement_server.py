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

"""Premium-profile gating on the FastMCP tool surface.

Exercises both entitlement sources (the stdio environment allowlist and the
HTTP OAuth scope) against the real bundled ``ACME_Premium`` premium profile.
"""

from __future__ import annotations

import pytest

from iso20022_bank_profile_mcp import server as server_mod
from iso20022_bank_profile_mcp.entitlement import ENTITLEMENTS_ENV
from iso20022_bank_profile_mcp.http import context as context_mod
from iso20022_bank_profile_mcp.models import ClearingProfile
from tests.conftest import PAIN_001

_PREMIUM = "ACME_Premium"


@pytest.fixture(autouse=True)
def _no_entitlement(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start each test with no ambient entitlement (env or scope)."""
    monkeypatch.delenv(ENTITLEMENTS_ENV, raising=False)


# --------------------------------------------------------------------------- #
# _entitled / _require_entitled                                              #
# --------------------------------------------------------------------------- #
def test_entitled_true_for_open_profile() -> None:
    """An open profile is entitled with no scopes and no allowlist."""
    profile = ClearingProfile(profile_id="Generic", market_practice="m")
    assert server_mod._entitled(profile) is True
    assert server_mod._require_entitled(profile) is None


def test_entitled_false_for_premium_without_grant() -> None:
    """A premium profile is not entitled by default."""
    profile = server_mod._engine.get(_PREMIUM)
    assert server_mod._entitled(profile) is False


# --------------------------------------------------------------------------- #
# get_profile gating                                                          #
# --------------------------------------------------------------------------- #
def test_get_premium_without_entitlement_errors() -> None:
    """Fetching a premium profile unentitled returns BP_NOT_ENTITLED."""
    result = server_mod.get_profile(_PREMIUM)
    assert result["error"]["code"] == "BP_NOT_ENTITLED"
    assert result["error"]["context"]["tier"] == "premium"


def test_get_premium_entitled_via_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An env allowlist entry unlocks the premium profile for ``get``."""
    monkeypatch.setenv(ENTITLEMENTS_ENV, _PREMIUM)
    result = server_mod.get_profile(_PREMIUM)
    assert result["profile_id"] == _PREMIUM
    assert "error" not in result


def test_get_premium_entitled_via_oauth_scope() -> None:
    """An OAuth premium scope unlocks the premium profile for ``get``."""
    token = context_mod._scopes_var.set(("profile:premium",))
    try:
        result = server_mod.get_profile(_PREMIUM)
    finally:
        context_mod._scopes_var.reset(token)
    assert result["profile_id"] == _PREMIUM
    assert "error" not in result


# --------------------------------------------------------------------------- #
# lint_payload gating                                                         #
# --------------------------------------------------------------------------- #
def test_lint_premium_without_entitlement_errors() -> None:
    """Linting against a premium profile unentitled sets BP_NOT_ENTITLED."""
    result = server_mod.lint_payload(PAIN_001, _PREMIUM)
    assert result["error"]["code"] == "BP_NOT_ENTITLED"
    assert result["findings"] == []


def test_lint_premium_entitled_via_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An env allowlist entry lets a premium profile lint and find issues."""
    monkeypatch.setenv(ENTITLEMENTS_ENV, _PREMIUM)
    result = server_mod.lint_payload(PAIN_001, _PREMIUM)
    assert result["error"] is None
    assert result["is_compliant"] is False
    assert {f["code"] for f in result["findings"]} == {
        "ACME_MISSING_COUNTRY",
        "ACME_NON_EUR",
    }


def test_lint_premium_entitled_via_oauth_scope() -> None:
    """An OAuth premium scope lets a premium profile lint."""
    token = context_mod._scopes_var.set(("profile:premium",))
    try:
        result = server_mod.lint_payload(PAIN_001, _PREMIUM)
    finally:
        context_mod._scopes_var.reset(token)
    assert result["error"] is None
    assert result["is_compliant"] is False
