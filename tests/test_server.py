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

"""The FastMCP tool surface and the ``main`` console entry point."""

from __future__ import annotations

import pytest

from iso20022_bank_profile_mcp import __version__
from iso20022_bank_profile_mcp import server as server_mod
from iso20022_bank_profile_mcp.errors import InvalidInputError
from tests.conftest import (
    NOT_XML,
    PAIN_001,
    PAIN_001_COMPLIANT,
)


# --------------------------------------------------------------------------- #
# _as_detail                                                                 #
# --------------------------------------------------------------------------- #
def test_as_detail_wraps_bank_profile_error() -> None:
    """A ``BankProfileError`` keeps its own code and locator."""
    detail = server_mod._as_detail(InvalidInputError("bad", locator="Ctry"))
    assert detail.code == "BP_INVALID_INPUT"
    assert detail.locator == "Ctry"


def test_as_detail_wraps_plain_exception() -> None:
    """A plain exception is normalised to the generic ``BP_ERROR`` code."""
    detail = server_mod._as_detail(ValueError("kaboom"))
    assert detail.code == "BP_ERROR"
    assert "kaboom" in detail.explanation


# --------------------------------------------------------------------------- #
# list_profiles                                                              #
# --------------------------------------------------------------------------- #
def test_list_profiles_tool() -> None:
    """``list_profiles`` returns a JSON-ready summary per profile."""
    profiles = server_mod.list_profiles()
    ids = {p["profile_id"] for p in profiles}
    assert ids == {
        "CBPR+",
        "FedNow",
        "SEPA_Instant",
        "Generic",
        "ACME_Premium",
    }
    cbpr = next(p for p in profiles if p["profile_id"] == "CBPR+")
    assert cbpr["rule_count"] == 2


def test_list_profiles_marks_tier_and_entitlement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Open profiles are entitled; premium is marked and gated by default."""
    monkeypatch.delenv("ISO20022_BANK_PROFILE_ENTITLEMENTS", raising=False)
    profiles = server_mod.list_profiles()
    by_id = {p["profile_id"]: p for p in profiles}
    assert by_id["CBPR+"]["tier"] == "open"
    assert by_id["CBPR+"]["entitled"] is True
    assert by_id["ACME_Premium"]["tier"] == "premium"
    assert by_id["ACME_Premium"]["entitled"] is False


# --------------------------------------------------------------------------- #
# get_profile                                                                #
# --------------------------------------------------------------------------- #
def test_get_profile_success() -> None:
    """``get_profile`` returns a full profile including rule bodies."""
    result = server_mod.get_profile("CBPR+")
    assert result["profile_id"] == "CBPR+"
    assert len(result["custom_rules"]) == 2


def test_get_profile_unknown_returns_error() -> None:
    """An unknown profile yields an ``{"error": ...}`` payload, not a raise."""
    result = server_mod.get_profile("NoSuch")
    assert result["error"]["code"] == "BP_UNKNOWN_PROFILE"


# --------------------------------------------------------------------------- #
# lint_payload                                                               #
# --------------------------------------------------------------------------- #
def test_lint_payload_compliant() -> None:
    """A compliant payload lints clean (no findings)."""
    result = server_mod.lint_payload(PAIN_001_COMPLIANT, "CBPR+")
    assert result["is_compliant"] is True
    assert result["findings"] == []
    assert result["error"] is None


def test_lint_payload_non_compliant() -> None:
    """A non-compliant CBPR+ payload surfaces its two findings."""
    result = server_mod.lint_payload(PAIN_001, "CBPR+")
    assert result["is_compliant"] is False
    codes = {f["code"] for f in result["findings"]}
    assert codes == {"CBPR_MISSING_COUNTRY", "CBPR_MISSING_TOWN"}


def test_lint_payload_unknown_profile_sets_error() -> None:
    """Linting against an unknown profile sets the response error."""
    result = server_mod.lint_payload(PAIN_001, "NoSuch")
    assert result["error"]["code"] == "BP_UNKNOWN_PROFILE"


def test_lint_payload_unparseable_sets_error() -> None:
    """Linting an unparseable payload sets the response error."""
    result = server_mod.lint_payload(NOT_XML, "CBPR+")
    assert result["error"]["code"] == "BP_INVALID_INPUT"


# --------------------------------------------------------------------------- #
# validate_profile_definition                                                #
# --------------------------------------------------------------------------- #
def test_validate_profile_definition_good() -> None:
    """A valid definition reports ``is_valid`` with its rule count."""
    definition = (
        '{"profile_id": "BankX", "market_practice": "House rules", '
        '"custom_rules": [{"rule_id": "x-ctry", '
        '"description": "Ctry required", "locator": "Ctry", '
        '"assertion": "required", "error_code": "X_MISSING_CTRY"}]}'
    )
    result = server_mod.validate_profile_definition(definition)
    assert result["is_valid"] is True
    assert result["profile_id"] == "BankX"
    assert result["rule_count"] == 1


def test_validate_profile_definition_bad() -> None:
    """A malformed definition reports invalid with an error detail."""
    result = server_mod.validate_profile_definition("{not json")
    assert result["is_valid"] is False
    assert result["errors"][0]["code"] == "BP_INVALID_PROFILE_DEFINITION"


# --------------------------------------------------------------------------- #
# main                                                                       #
# --------------------------------------------------------------------------- #
def test_main_version_exits(capsys: pytest.CaptureFixture[str]) -> None:
    """``main(['--version'])`` prints the version and exits cleanly."""
    with pytest.raises(SystemExit) as info:
        server_mod.main(["--version"])
    assert info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_main_runs_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """``main([])`` parses args and hands off to the FastMCP run loop."""
    called: list[bool] = []
    monkeypatch.setattr(server_mod.server, "run", lambda: called.append(True))
    server_mod.main([])
    assert called == [True]


def test_main_transport_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--transport=http`` hands off to the HTTP transport with the bind."""
    from iso20022_bank_profile_mcp.http import transport as transport_mod

    calls: list[tuple[object, str]] = []
    monkeypatch.setattr(
        transport_mod,
        "run_http",
        lambda srv, bind: calls.append((srv, bind)),
    )
    server_mod.main(["--transport=http", "--bind=0.0.0.0:9000"])
    assert calls == [(server_mod.server, "0.0.0.0:9000")]


def test_main_transport_http_default_bind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--transport=http`` with no ``--bind`` uses the default bind."""
    from iso20022_bank_profile_mcp.http import transport as transport_mod

    calls: list[tuple[object, str]] = []
    monkeypatch.setattr(
        transport_mod,
        "run_http",
        lambda srv, bind: calls.append((srv, bind)),
    )
    server_mod.main(["--transport=http"])
    assert calls == [(server_mod.server, transport_mod.DEFAULT_BIND)]
