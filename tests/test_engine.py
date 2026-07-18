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

"""The clearing-profile policy engine: loading, registration, evaluation."""

from __future__ import annotations

import pytest

from iso20022_bank_profile_mcp import engine as engine_mod
from iso20022_bank_profile_mcp.engine import (
    ProfileEngine,
    _assertion_is_known,
    _find_text,
    _local,
)
from iso20022_bank_profile_mcp.errors import (
    InvalidInputError,
    InvalidProfileDefinitionError,
    UnknownProfileError,
)
from iso20022_bank_profile_mcp.models import ClearingProfile, ProfileRule
from tests.conftest import (
    NOT_XML,
    PAIN_001,
    PAIN_001_COMPLIANT,
    PAIN_001_EMPTY_CTRY,
    SEPA_EUR_BAD,
    SEPA_EUR_GOOD,
    SEPA_USD,
)


# --------------------------------------------------------------------------- #
# Module helpers                                                              #
# --------------------------------------------------------------------------- #
def test_local_strips_namespace() -> None:
    """``_local`` returns the local name, dropping any ``{namespace}``."""
    assert _local("{urn:iso:std:iso:20022}Ctry") == "Ctry"
    assert _local("Ctry") == "Ctry"


def test_find_text_matches_namespaced_element() -> None:
    """``_find_text`` finds a namespaced element and returns its text."""
    from defusedxml.ElementTree import fromstring

    root = fromstring(PAIN_001_COMPLIANT)
    assert _find_text(root, "Ctry") == "GB"


def test_find_text_skips_empty_text_and_misses() -> None:
    """An element present but empty (text None) is treated as a miss."""
    from defusedxml.ElementTree import fromstring

    root = fromstring(PAIN_001_EMPTY_CTRY)
    assert _find_text(root, "Ctry") is None
    assert _find_text(root, "DoesNotExist") is None


def test_assertion_is_known() -> None:
    """Known verbs are recognised; anything else is rejected."""
    assert _assertion_is_known("required")
    assert _assertion_is_known("equals:EUR")
    assert _assertion_is_known("if:Ccy=EUR:equals:SLEV")
    assert not _assertion_is_known("frobnicate")


# --------------------------------------------------------------------------- #
# Loading & registration                                                     #
# --------------------------------------------------------------------------- #
def test_from_bundled_loads_five_profiles(engine: ProfileEngine) -> None:
    """The five profiles (four open + one premium) ship bundled."""
    ids = {p.profile_id for p in engine.list_profiles()}
    assert ids == {
        "CBPR+",
        "FedNow",
        "SEPA_Instant",
        "Generic",
        "ACME_Premium",
    }


def test_from_bundled_marks_premium_tier(engine: ProfileEngine) -> None:
    """Open baseline profiles are ``open``; ACME_Premium is ``premium``."""
    assert engine.get("CBPR+").tier == "open"
    assert engine.get("ACME_Premium").tier == "premium"


class _FakeEntry:
    """A directory entry exposing ``.name`` and ``.read_text``."""

    def __init__(self, name: str, text: str = "") -> None:
        """Store the entry name and its text payload."""
        self.name = name
        self._text = text

    def read_text(self, encoding: str = "utf-8") -> str:
        """Return the stored text payload."""
        return self._text


class _FakeDir:
    """A traversable directory yielding fixed entries from ``iterdir``."""

    def __init__(self, entries: list[_FakeEntry]) -> None:
        """Store the entries this directory yields."""
        self._entries = entries

    def iterdir(self) -> list[_FakeEntry]:
        """Return the fixed directory entries."""
        return list(self._entries)


class _FakeRoot:
    """A traversable whose ``joinpath`` returns the fake profiles dir."""

    def __init__(self, directory: _FakeDir) -> None:
        """Store the directory ``joinpath`` returns."""
        self._dir = directory

    def joinpath(self, name: str) -> _FakeDir:
        """Return the stored fake directory, ignoring ``name``."""
        return self._dir


def test_from_bundled_skips_non_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-``.json`` directory entries are skipped during loading."""
    profile_json = (
        '{"profile_id": "OnlyOne", "market_practice": "m", '
        '"supported_messages": [], "custom_rules": []}'
    )
    directory = _FakeDir(
        [
            _FakeEntry("README.txt", "ignore me"),
            _FakeEntry("only_one.json", profile_json),
        ]
    )
    monkeypatch.setattr(
        engine_mod.resources, "files", lambda pkg: _FakeRoot(directory)
    )
    loaded = ProfileEngine.from_bundled()
    assert [p.profile_id for p in loaded.list_profiles()] == ["OnlyOne"]


def test_get_known_profile(engine: ProfileEngine) -> None:
    """``get`` returns a registered profile."""
    assert engine.get("CBPR+").profile_id == "CBPR+"


def test_get_unknown_profile_raises(engine: ProfileEngine) -> None:
    """``get`` raises ``UnknownProfileError`` and lists what is available."""
    with pytest.raises(UnknownProfileError) as info:
        engine.get("NoSuch")
    assert "available" in info.value.context


def test_register_and_replace() -> None:
    """Registering the same id replaces the prior profile."""
    engine = ProfileEngine({})
    engine.register(ClearingProfile(profile_id="X", market_practice="v1"))
    engine.register(ClearingProfile(profile_id="X", market_practice="v2"))
    assert len(engine.list_profiles()) == 1
    assert engine.get("X").market_practice == "v2"


# --------------------------------------------------------------------------- #
# apply: assertion evaluation                                                #
# --------------------------------------------------------------------------- #
def test_apply_unknown_profile_raises(engine: ProfileEngine) -> None:
    """An unregistered profile id raises ``UnknownProfileError``."""
    with pytest.raises(UnknownProfileError):
        engine.apply("NoSuch", PAIN_001)


def test_apply_unparseable_xml_raises(engine: ProfileEngine) -> None:
    """Unparseable XML raises ``InvalidInputError``."""
    with pytest.raises(InvalidInputError) as info:
        engine.apply("CBPR+", NOT_XML)
    assert info.value.code == "BP_INVALID_INPUT"


def test_required_rule_violated(engine: ProfileEngine) -> None:
    """Missing required elements produce one finding per rule."""
    findings = engine.apply("CBPR+", PAIN_001)
    assert {f.code for f in findings} == {
        "CBPR_MISSING_COUNTRY",
        "CBPR_MISSING_TOWN",
    }
    assert findings[0].context == {
        "rule_id": "cbpr-ctry",
        "severity": "error",
    }


def test_required_rule_satisfied(engine: ProfileEngine) -> None:
    """A fully structured address satisfies the required rules."""
    assert engine.apply("CBPR+", PAIN_001_COMPLIANT) == []


def test_generic_profile_has_no_rules(engine: ProfileEngine) -> None:
    """The Generic profile carries no rules, so it never finds anything."""
    assert engine.apply("Generic", PAIN_001) == []


def _equals_profile() -> ClearingProfile:
    """A one-rule profile asserting the Ccy element equals EUR."""
    return ClearingProfile(
        profile_id="EqCheck",
        market_practice="test",
        custom_rules=(
            ProfileRule(
                rule_id="eq-ccy",
                description="Ccy must be EUR.",
                locator="Ccy",
                assertion="equals:EUR",
                error_code="CCY_NOT_EUR",
            ),
        ),
    )


def test_equals_rule_satisfied(engine: ProfileEngine) -> None:
    """A registered equals-rule passes when the text matches."""
    engine.register(_equals_profile())
    assert engine.apply("EqCheck", SEPA_EUR_BAD) == []


def test_equals_rule_violated(engine: ProfileEngine) -> None:
    """An equals-rule fails when the element text differs."""
    engine.register(_equals_profile())
    findings = engine.apply("EqCheck", SEPA_USD)
    assert [f.code for f in findings] == ["CCY_NOT_EUR"]


def test_conditional_rule_not_applicable(engine: ProfileEngine) -> None:
    """The SEPA conditional does not fire when the condition is unmet."""
    assert engine.apply("SEPA_Instant", SEPA_USD) == []


def test_conditional_rule_violated(engine: ProfileEngine) -> None:
    """An EUR payment whose ChrgBr is not SLEV violates the SEPA rule."""
    findings = engine.apply("SEPA_Instant", SEPA_EUR_BAD)
    assert [f.code for f in findings] == ["SEPA_CHRGBR_NOT_SLEV"]


def test_conditional_rule_satisfied(engine: ProfileEngine) -> None:
    """An EUR payment with ChrgBr SLEV satisfies the SEPA rule."""
    assert engine.apply("SEPA_Instant", SEPA_EUR_GOOD) == []


# --------------------------------------------------------------------------- #
# validate_definition                                                        #
# --------------------------------------------------------------------------- #
def test_validate_definition_valid(engine: ProfileEngine) -> None:
    """A well-formed definition parses back into a profile."""
    definition = (
        '{"profile_id": "BankX", "market_practice": "House rules", '
        '"supported_messages": ["pacs.008"], "custom_rules": ['
        '{"rule_id": "x-ctry", "description": "Ctry required", '
        '"locator": "Ctry", "assertion": "required", '
        '"error_code": "X_MISSING_CTRY"}]}'
    )
    profile = engine.validate_definition(definition)
    assert profile.profile_id == "BankX"
    assert len(profile.custom_rules) == 1


def test_validate_definition_empty_rules(engine: ProfileEngine) -> None:
    """A definition with no rules validates (the rule loop is skipped)."""
    definition = (
        '{"profile_id": "Bare", "market_practice": "m", '
        '"supported_messages": [], "custom_rules": []}'
    )
    assert engine.validate_definition(definition).custom_rules == ()


def test_validate_definition_malformed_json(engine: ProfileEngine) -> None:
    """Malformed JSON raises ``InvalidProfileDefinitionError``."""
    with pytest.raises(InvalidProfileDefinitionError) as info:
        engine.validate_definition("{not json")
    assert "not valid JSON" in info.value.explanation


def test_validate_definition_schema_invalid(engine: ProfileEngine) -> None:
    """A schema-invalid definition (extra field) is rejected with errors."""
    definition = '{"profile_id": "Bad", "market_practice": "m", "surprise": 1}'
    with pytest.raises(InvalidProfileDefinitionError) as info:
        engine.validate_definition(definition)
    assert "errors" in info.value.context


def test_validate_definition_missing_required_field(
    engine: ProfileEngine,
) -> None:
    """A definition missing a required field fails schema validation."""
    with pytest.raises(InvalidProfileDefinitionError):
        engine.validate_definition('{"market_practice": "m"}')


def test_validate_definition_unknown_assertion(
    engine: ProfileEngine,
) -> None:
    """A rule with an unknown verb raises, locating the offending rule."""
    definition = (
        '{"profile_id": "BankY", "market_practice": "m", '
        '"custom_rules": [{"rule_id": "weird", '
        '"description": "d", "locator": "Ctry", '
        '"assertion": "frobnicate", "error_code": "E"}]}'
    )
    with pytest.raises(InvalidProfileDefinitionError) as info:
        engine.validate_definition(definition)
    assert info.value.locator == "weird"
    assert info.value.context["known_verbs"] == ["required", "equals:", "if:"]
