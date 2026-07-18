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

"""The clearing-profile engine.

Profiles capture market-practice assertions that lie *beyond* structural XSD
validation (e.g. "every postal address must carry a Ctry element"). They are
pure data — bundled JSON for the open baseline profiles, and loadable at
runtime for bank-specific rule packs. XML is parsed with ``defusedxml`` only.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from defusedxml.ElementTree import fromstring
from pydantic import ValidationError

from iso20022_bank_profile_mcp.errors import (
    ErrorDetail,
    InvalidInputError,
    InvalidProfileDefinitionError,
    UnknownProfileError,
)
from iso20022_bank_profile_mcp.models import ClearingProfile, ProfileRule

#: The assertion verbs the engine can evaluate.
_KNOWN_ASSERTIONS = ("required", "equals:", "if:")


def _local(tag: str) -> str:
    """Return an element's local name, stripping any ``{namespace}``."""
    return tag.rsplit("}", 1)[-1]


def _find_text(root: Any, element: str) -> str | None:
    """Return the text of the first descendant with local name ``element``."""
    for node in root.iter():
        if _local(node.tag) == element and node.text is not None:
            return str(node.text).strip()
    return None


def _assertion_is_known(assertion: str) -> bool:
    """Return whether ``assertion`` uses a verb the engine can evaluate."""
    return any(assertion.startswith(verb) for verb in _KNOWN_ASSERTIONS)


class ProfileEngine:
    """Loads clearing profiles and evaluates them against a payload."""

    def __init__(self, profiles: dict[str, ClearingProfile]) -> None:
        """Store the registered profiles keyed by ``profile_id``."""
        self._profiles = dict(profiles)

    @classmethod
    def from_bundled(cls) -> ProfileEngine:
        """Load the baseline (open-source) profiles bundled with the package."""
        profiles: dict[str, ClearingProfile] = {}
        root = resources.files("iso20022_bank_profile_mcp.data").joinpath(
            "profiles"
        )
        for entry in root.iterdir():
            if entry.name.endswith(".json"):
                data = json.loads(entry.read_text(encoding="utf-8"))
                profile = ClearingProfile.model_validate(data)
                profiles[profile.profile_id] = profile
        return cls(profiles)

    def list_profiles(self) -> list[ClearingProfile]:
        """Return every registered profile."""
        return list(self._profiles.values())

    def get(self, profile_id: str) -> ClearingProfile:
        """Return one profile, raising :class:`UnknownProfileError` if absent."""
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise UnknownProfileError(
                f"No clearing profile registered for {profile_id!r}.",
                context={"available": sorted(self._profiles)},
            )
        return profile

    def register(self, profile: ClearingProfile) -> None:
        """Register (or replace) a profile, e.g. a bank-specific rule pack."""
        self._profiles[profile.profile_id] = profile

    def validate_definition(self, definition: str) -> ClearingProfile:
        """Parse and validate a raw JSON profile definition.

        Raises :class:`InvalidProfileDefinitionError` when the JSON is
        malformed, the schema does not fit, or a rule uses an assertion verb
        the engine cannot evaluate.
        """
        try:
            data = json.loads(definition)
        except json.JSONDecodeError as exc:
            raise InvalidProfileDefinitionError(
                f"Definition is not valid JSON: {exc}"
            ) from exc
        try:
            profile = ClearingProfile.model_validate(data)
        except ValidationError as exc:
            raise InvalidProfileDefinitionError(
                f"Definition does not match the profile schema: "
                f"{exc.error_count()} error(s).",
                context={"errors": exc.errors(include_url=False)},
            ) from exc
        for rule in profile.custom_rules:
            if not _assertion_is_known(rule.assertion):
                raise InvalidProfileDefinitionError(
                    f"Rule {rule.rule_id!r} uses an unknown assertion "
                    f"{rule.assertion!r}.",
                    locator=rule.rule_id,
                    context={"known_verbs": list(_KNOWN_ASSERTIONS)},
                )
        return profile

    def apply(self, profile_id: str, xml_content: str) -> list[ErrorDetail]:
        """Evaluate ``profile_id`` against ``xml_content``.

        Returns an ordered list of findings (empty when compliant). Raises
        :class:`UnknownProfileError` for an unregistered id and
        :class:`InvalidInputError` for unparseable XML.
        """
        profile = self.get(profile_id)
        try:
            root = fromstring(xml_content)
        except Exception as exc:  # noqa: BLE001 - normalize to a typed error
            raise InvalidInputError(
                f"Payload is not parseable XML: {exc}"
            ) from exc
        return [
            finding
            for rule in profile.custom_rules
            if (finding := self._evaluate(rule, root)) is not None
        ]

    def _evaluate(self, rule: ProfileRule, root: Any) -> ErrorDetail | None:
        """Evaluate one rule; return a finding when it is violated."""
        assertion = rule.assertion
        if assertion == "required":
            violated = _find_text(root, rule.locator) is None
        elif assertion.startswith("equals:"):
            expected = assertion.split(":", 1)[1]
            violated = _find_text(root, rule.locator) != expected
        elif assertion.startswith("if:"):
            violated = self._eval_conditional(assertion, rule.locator, root)
        else:  # pragma: no cover - guarded by validate_definition upstream
            violated = False
        if not violated:
            return None
        return ErrorDetail(
            code=rule.error_code,
            locator=rule.locator,
            explanation=rule.description,
            context={"rule_id": rule.rule_id, "severity": rule.severity},
        )

    def _eval_conditional(
        self, assertion: str, locator: str, root: Any
    ) -> bool:
        """Evaluate an ``if:<elem>=<val>:equals:<val2>`` assertion."""
        _, condition, _, expected = assertion.split(":", 3)
        cond_elem, cond_val = condition.split("=", 1)
        if _find_text(root, cond_elem) != cond_val:
            return False  # condition not met -> rule does not apply
        return _find_text(root, locator) != expected
