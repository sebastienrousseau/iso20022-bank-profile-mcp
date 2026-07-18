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

"""Per-request context variables for the HTTP transport."""

from __future__ import annotations

from iso20022_bank_profile_mcp.http import context as context_mod
from iso20022_bank_profile_mcp.http.context import (
    TENANT_HEADER,
    current_scopes,
    current_tenant,
)


def test_tenant_header_constant() -> None:
    """The tenant header name is the documented ``X-MCP-Tenant``."""
    assert TENANT_HEADER == "X-MCP-Tenant"


def test_defaults_are_empty() -> None:
    """Outside any request, tenant is ``None`` and scopes are empty."""
    assert current_tenant() is None
    assert current_scopes() == ()


def test_current_tenant_reads_context_var() -> None:
    """``current_tenant`` reflects the tenant context variable."""
    token = context_mod._tenant_var.set("acme")
    try:
        assert current_tenant() == "acme"
    finally:
        context_mod._tenant_var.reset(token)


def test_current_scopes_reads_context_var() -> None:
    """``current_scopes`` reflects the scopes context variable."""
    token = context_mod._scopes_var.set(("profile:premium",))
    try:
        assert current_scopes() == ("profile:premium",)
    finally:
        context_mod._scopes_var.reset(token)
