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

"""Model Context Protocol (MCP) server for bank-specific clearing profiles.

This server manages, validates, and serves the market-practice rule packs that
sit beyond structural XSD validation. It is a fully local, closed-world server
(no network surface, no sub-servers): every tool returns typed, JSON-
serializable data and an ``{"error": ...}``-shaped payload on any failure,
never a traceback.

Launch as a console script (``iso20022-bank-profile-mcp``) or configure it in
an MCP client. The transport is stdio (FastMCP's default).
"""

from __future__ import annotations

import argparse
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from iso20022_bank_profile_mcp import __version__
from iso20022_bank_profile_mcp.engine import ProfileEngine
from iso20022_bank_profile_mcp.errors import BankProfileError, ErrorDetail
from iso20022_bank_profile_mcp.models import (
    LintRequest,
    LintResponse,
    ProfileSummary,
    ValidateProfileRequest,
    ValidateProfileResponse,
)

server = FastMCP("iso20022-bank-profile")
# FastMCP does not accept a version kwarg; set it so serverInfo.version is
# coherent with the package version.
server._mcp_server.version = __version__

# Module singleton. Tests substitute ``_engine`` with a fixture-loaded engine.
_engine: ProfileEngine = ProfileEngine.from_bundled()

# Every tool is a pure, local, read-only, idempotent, closed-world lookup.
_PURE_READ = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def _as_detail(exc: Exception) -> ErrorDetail:
    """Render any exception as a serializable :class:`ErrorDetail`."""
    if isinstance(exc, BankProfileError):
        return exc.to_detail()
    return ErrorDetail(code="BP_ERROR", explanation=f"Unexpected error: {exc}")


@server.tool(title="List clearing profiles", annotations=_PURE_READ)
def list_profiles() -> list[dict[str, Any]]:
    """List the available clearing profiles as lightweight summaries.

    Use this to discover the ``profile_id`` values the other tools accept.
    """
    summaries = [
        ProfileSummary(
            profile_id=p.profile_id,
            market_practice=p.market_practice,
            supported_messages=p.supported_messages,
            rule_count=len(p.custom_rules),
        )
        for p in _engine.list_profiles()
    ]
    return [s.model_dump(mode="json") for s in summaries]


@server.tool(title="Get a clearing profile", annotations=_PURE_READ)
def get_profile(
    profile_id: Annotated[
        str, Field(description="The profile to fetch (see list_profiles).")
    ],
) -> dict[str, Any]:
    """Return one clearing profile in full, including its rule bodies.

    Args:
        profile_id: The clearing profile identifier.
    """
    try:
        return _engine.get(profile_id).model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001 - boundary: return data, not trace
        return {"error": _as_detail(exc).model_dump(mode="json")}


@server.tool(title="Lint a payload against a profile", annotations=_PURE_READ)
def lint_payload(
    payload_content: Annotated[
        str, Field(description="Raw ISO 20022 payload text (not a path).")
    ],
    profile_id: Annotated[
        str, Field(description="The clearing profile to lint against.")
    ],
) -> dict[str, Any]:
    """Evaluate a payload against a clearing profile and return findings.

    Args:
        payload_content: The raw ISO 20022 message text.
        profile_id: The clearing profile to lint against.
    """
    request = LintRequest(
        payload_content=payload_content, profile_id=profile_id
    )
    try:
        findings = _engine.apply(request.profile_id, request.payload_content)
        response = LintResponse(
            profile_id=request.profile_id,
            is_compliant=not findings,
            findings=tuple(findings),
        )
    except Exception as exc:  # noqa: BLE001 - boundary: return data, not trace
        response = LintResponse(profile_id=profile_id, error=_as_detail(exc))
    return response.model_dump(mode="json")


@server.tool(title="Validate a profile definition", annotations=_PURE_READ)
def validate_profile_definition(
    definition_content: Annotated[
        str,
        Field(description="A profile / rule-pack definition as JSON text."),
    ],
) -> dict[str, Any]:
    """Validate a bank-supplied profile / rule-pack definition (raw JSON).

    Args:
        definition_content: The candidate profile definition, as JSON text.
    """
    request = ValidateProfileRequest(definition_content=definition_content)
    try:
        profile = _engine.validate_definition(request.definition_content)
        response = ValidateProfileResponse(
            is_valid=True,
            profile_id=profile.profile_id,
            rule_count=len(profile.custom_rules),
        )
    except Exception as exc:  # noqa: BLE001 - boundary: return data, not trace
        response = ValidateProfileResponse(
            is_valid=False, errors=(_as_detail(exc),)
        )
    return response.model_dump(mode="json")


def main(argv: list[str] | None = None) -> None:
    """Run the MCP server over stdio."""
    parser = argparse.ArgumentParser(
        prog="iso20022-bank-profile-mcp",
        description="ISO 20022 bank clearing-profile MCP server (stdio).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"iso20022-bank-profile-mcp {__version__}",
    )
    parser.parse_args(argv)
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
