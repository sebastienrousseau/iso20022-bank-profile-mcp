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

"""Request/response schemas: extra-field rejection and round-tripping."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from iso20022_bank_profile_mcp.errors import ErrorDetail
from iso20022_bank_profile_mcp.models import (
    ClearingProfile,
    LintRequest,
    LintResponse,
    ProfileRule,
    ProfileSummary,
    ValidateProfileRequest,
    ValidateProfileResponse,
)


@pytest.mark.parametrize(
    ("cls", "kwargs"),
    [
        (
            LintRequest,
            {"payload_content": "<x/>", "profile_id": "CBPR+"},
        ),
        (ValidateProfileRequest, {"definition_content": "{}"}),
    ],
)
def test_requests_forbid_extra_fields(
    cls: type, kwargs: dict[str, object]
) -> None:
    """Every request model rejects unexpected keys (``extra='forbid'``)."""
    cls(**kwargs)  # baseline is accepted
    with pytest.raises(ValidationError):
        cls(**kwargs, unexpected="nope")


def test_profile_rule_defaults_severity() -> None:
    """``ProfileRule.severity`` defaults to ``error`` and forbids extras."""
    rule = ProfileRule(
        rule_id="r1",
        description="d",
        locator="Ctry",
        assertion="required",
        error_code="X_MISSING",
    )
    assert rule.severity == "error"
    with pytest.raises(ValidationError):
        ProfileRule(
            rule_id="r1",
            description="d",
            locator="Ctry",
            assertion="required",
            error_code="X_MISSING",
            surprise="nope",
        )


def test_profile_rule_rejects_bad_severity() -> None:
    """``severity`` is constrained to the info/warning/error literal."""
    with pytest.raises(ValidationError):
        ProfileRule(
            rule_id="r1",
            description="d",
            locator="Ctry",
            assertion="required",
            error_code="X_MISSING",
            severity="fatal",
        )


def test_clearing_profile_round_trip() -> None:
    """A clearing profile with a nested rule round-trips through JSON."""
    profile = ClearingProfile(
        profile_id="X",
        market_practice="Demo",
        supported_messages=("pain.001",),
        custom_rules=(
            ProfileRule(
                rule_id="r1",
                description="d",
                locator="Ctry",
                assertion="required",
                error_code="X_MISSING",
            ),
        ),
    )
    again = ClearingProfile.model_validate(profile.model_dump(mode="json"))
    assert again == profile
    assert again.custom_rules[0].severity == "error"


def test_profile_summary_defaults() -> None:
    """A summary defaults its message list and rule count."""
    summary = ProfileSummary(profile_id="X", market_practice="Demo")
    assert summary.supported_messages == ()
    assert summary.rule_count == 0


def test_lint_response_round_trip() -> None:
    """A lint response with a finding round-trips through JSON."""
    detail = ErrorDetail(code="C", locator="Ctry", explanation="e")
    resp = LintResponse(
        profile_id="CBPR+",
        is_compliant=False,
        findings=(detail,),
    )
    again = LintResponse.model_validate(resp.model_dump(mode="json"))
    assert again == resp
    assert again.error is None


def test_validate_profile_response_round_trip() -> None:
    """A validate-profile response round-trips through JSON."""
    resp = ValidateProfileResponse(
        is_valid=True,
        profile_id="X",
        rule_count=2,
    )
    again = ValidateProfileResponse.model_validate(
        resp.model_dump(mode="json")
    )
    assert again == resp
