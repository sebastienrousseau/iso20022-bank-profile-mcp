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

"""Premium-profile entitlement resolution: scopes ORed with an allowlist."""

from __future__ import annotations

import pytest

from iso20022_bank_profile_mcp.entitlement import (
    ENTITLEMENTS_ENV,
    PREMIUM_SCOPE,
    allowlist_from_env,
    is_entitled,
)


# --------------------------------------------------------------------------- #
# is_entitled                                                                 #
# --------------------------------------------------------------------------- #
def test_open_tier_always_entitled() -> None:
    """An open-tier profile needs no scope or allowlist entry."""
    assert is_entitled("Generic", "open", (), frozenset()) is True


def test_premium_with_premium_scope() -> None:
    """The blanket premium scope entitles any premium profile."""
    assert (
        is_entitled("ACME_Premium", "premium", (PREMIUM_SCOPE,), frozenset())
        is True
    )


def test_premium_with_profile_specific_scope() -> None:
    """A ``profile:<id>`` scope entitles exactly that premium profile."""
    assert (
        is_entitled(
            "ACME_Premium",
            "premium",
            ("profile:ACME_Premium",),
            frozenset(),
        )
        is True
    )


def test_premium_with_id_in_allowlist() -> None:
    """The profile id appearing in the allowlist grants access."""
    assert (
        is_entitled("ACME_Premium", "premium", (), frozenset({"ACME_Premium"}))
        is True
    )


def test_premium_with_wildcard_allowlist() -> None:
    """A ``*`` allowlist entry grants every premium profile."""
    assert is_entitled("ACME_Premium", "premium", (), frozenset({"*"})) is True


def test_premium_without_grant_denied() -> None:
    """Premium with neither a granting scope nor an allowlist entry fails."""
    assert (
        is_entitled(
            "ACME_Premium",
            "premium",
            ("profile:Other",),
            frozenset({"Other"}),
        )
        is False
    )


# --------------------------------------------------------------------------- #
# allowlist_from_env                                                          #
# --------------------------------------------------------------------------- #
def test_allowlist_unset_is_empty() -> None:
    """An unset variable yields the empty allowlist."""
    assert allowlist_from_env({}) == frozenset()


def test_allowlist_comma_separated() -> None:
    """Comma-separated ids parse into a set."""
    got = allowlist_from_env({ENTITLEMENTS_ENV: "ACME_Premium,Other"})
    assert got == frozenset({"ACME_Premium", "Other"})


def test_allowlist_space_separated() -> None:
    """Space-separated ids (and mixed separators) parse into a set."""
    got = allowlist_from_env({ENTITLEMENTS_ENV: "ACME_Premium  Other, Third"})
    assert got == frozenset({"ACME_Premium", "Other", "Third"})


def test_allowlist_reads_os_environ_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``environ=None`` reads the live ``os.environ``."""
    monkeypatch.setenv(ENTITLEMENTS_ENV, "ACME_Premium")
    assert allowlist_from_env() == frozenset({"ACME_Premium"})
