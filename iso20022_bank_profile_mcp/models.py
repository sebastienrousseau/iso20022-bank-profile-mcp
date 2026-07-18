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

"""Pydantic schemas for the bank-profile tools.

All tool inputs and outputs are typed models: the MCP surface never accepts or
emits an untyped ``dict``. Payloads and rule-pack definitions are passed as
raw string content, never as server filesystem paths.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from iso20022_bank_profile_mcp.errors import ErrorDetail


class ProfileRule(BaseModel):
    """A single declarative profile assertion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    description: str
    #: The local name of the element the rule inspects.
    locator: str
    #: A declarative condition evaluated by the engine (``required``,
    #: ``equals:<v>``, or ``if:<elem>=<v>:equals:<v2>``).
    assertion: str
    error_code: str
    severity: Literal["info", "warning", "error"] = "error"


class ClearingProfile(BaseModel):
    """A market-practice / clearing-scheme rule set beyond XSD checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    market_practice: str
    supported_messages: tuple[str, ...] = ()
    custom_rules: tuple[ProfileRule, ...] = ()


class ProfileSummary(BaseModel):
    """A lightweight profile descriptor for discovery (no rule bodies)."""

    model_config = ConfigDict(frozen=True)

    profile_id: str
    market_practice: str
    supported_messages: tuple[str, ...] = ()
    rule_count: int = 0


class LintRequest(BaseModel):
    """Input for :func:`lint_payload`."""

    model_config = ConfigDict(extra="forbid")

    payload_content: str = Field(description="Raw ISO 20022 payload text.")
    profile_id: str = Field(
        description="The clearing profile to lint against."
    )


class LintResponse(BaseModel):
    """Findings from linting a payload against a clearing profile."""

    model_config = ConfigDict(frozen=True)

    profile_id: str = ""
    is_compliant: bool = False
    findings: tuple[ErrorDetail, ...] = ()
    error: ErrorDetail | None = None


class ValidateProfileRequest(BaseModel):
    """Input for :func:`validate_profile_definition`."""

    model_config = ConfigDict(extra="forbid")

    definition_content: str = Field(
        description="A bank profile / rule-pack definition as raw JSON text."
    )


class ValidateProfileResponse(BaseModel):
    """The outcome of validating a profile / rule-pack definition."""

    model_config = ConfigDict(frozen=True)

    is_valid: bool = False
    profile_id: str = ""
    rule_count: int = 0
    errors: tuple[ErrorDetail, ...] = ()
    error: ErrorDetail | None = None


ClearingProfile.model_rebuild()
