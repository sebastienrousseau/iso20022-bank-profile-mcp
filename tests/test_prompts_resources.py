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

"""The FastMCP prompt and resource surface (the MCP "Trinity")."""

from __future__ import annotations

import json

from iso20022_bank_profile_mcp import server as server_mod


# --------------------------------------------------------------------------- #
# Prompt: lint_bank_payload                                                   #
# --------------------------------------------------------------------------- #
def test_prompt_is_registered() -> None:
    """The linting-workflow prompt is registered with its title."""
    prompts = server_mod.server._prompt_manager.list_prompts()
    by_name = {p.name: p for p in prompts}
    assert "lint_bank_payload" in by_name
    assert (
        by_name["lint_bank_payload"].title
        == "Lint a bank payload against a clearing profile"
    )


def test_prompt_default_profile_teaches_workflow() -> None:
    """With the default arg the prompt names the workflow and CBPR+."""
    guidance = server_mod.lint_bank_payload()
    assert "'CBPR+'" in guidance
    assert "SWIFT CBPR+ UG2026" in guidance  # market practice, known branch
    assert "list_profiles" in guidance
    assert "get_profile" in guidance
    assert "lint_payload" in guidance


def test_prompt_unknown_profile_falls_back() -> None:
    """An unknown profile_id takes the fallback (except) branch."""
    guidance = server_mod.lint_bank_payload("NoSuch")
    assert "'NoSuch'" in guidance
    assert "unrecognised profile" in guidance
    # Workflow is still taught even when the id is unknown.
    assert "list_profiles" in guidance


# --------------------------------------------------------------------------- #
# Static resource: bankprofile://profiles                                     #
# --------------------------------------------------------------------------- #
def test_static_resource_is_registered() -> None:
    """The profiles resource is registered as a static JSON resource."""
    resources = server_mod.server._resource_manager.list_resources()
    by_uri = {str(r.uri): r for r in resources}
    assert "bankprofile://profiles" in by_uri
    res = by_uri["bankprofile://profiles"]
    assert res.title == "All clearing profiles"
    assert res.mime_type == "application/json"


def test_static_resource_mirrors_list_profiles() -> None:
    """The static resource serialises exactly what list_profiles returns."""
    payload = json.loads(server_mod.profiles_resource())
    assert payload == server_mod.list_profiles()
    assert {p["profile_id"] for p in payload} == {
        "CBPR+",
        "FedNow",
        "SEPA_Instant",
        "Generic",
        "ACME_Premium",
    }


# --------------------------------------------------------------------------- #
# Templated resource: bankprofile://profile/{profile_id}                      #
# --------------------------------------------------------------------------- #
def test_templated_resource_is_registered() -> None:
    """The single-profile resource is registered as a URI template."""
    templates = server_mod.server._resource_manager.list_templates()
    by_tmpl = {t.uri_template: t for t in templates}
    assert "bankprofile://profile/{profile_id}" in by_tmpl
    tmpl = by_tmpl["bankprofile://profile/{profile_id}"]
    assert tmpl.title == "A single clearing profile"
    assert tmpl.mime_type == "application/json"


def test_templated_resource_known_profile() -> None:
    """A known id serialises the full profile, mirroring get_profile."""
    payload = json.loads(server_mod.profile_resource("CBPR+"))
    assert payload == server_mod.get_profile("CBPR+")
    assert payload["profile_id"] == "CBPR+"


def test_templated_resource_unknown_profile_serialises_error() -> None:
    """An unknown id serialises the same {"error": ...} payload, no raise."""
    payload = json.loads(server_mod.profile_resource("NoSuch"))
    assert payload["error"]["code"] == "BP_UNKNOWN_PROFILE"
