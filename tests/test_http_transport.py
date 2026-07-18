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

"""The streamable-HTTP transport: bind parsing, static-token auth, wiring."""

from __future__ import annotations

import json

import httpx
import pytest

from iso20022_bank_profile_mcp.http import context as context_mod
from iso20022_bank_profile_mcp.http import oauth as oauth_mod
from iso20022_bank_profile_mcp.http import transport as transport_mod
from iso20022_bank_profile_mcp.http.transport import (
    DEFAULT_BIND,
    TOKEN_ENV,
    BearerTokenMiddleware,
    build_http_app,
    parse_bind,
    run_http,
)


# --------------------------------------------------------------------------- #
# parse_bind                                                                  #
# --------------------------------------------------------------------------- #
def test_parse_bind_valid() -> None:
    """A well-formed ``HOST:PORT`` parses into its parts."""
    assert parse_bind("0.0.0.0:8080") == ("0.0.0.0", 8080)


def test_parse_bind_no_colon() -> None:
    """A bind with no colon is rejected."""
    with pytest.raises(ValueError, match="HOST:PORT"):
        parse_bind("localhost")


def test_parse_bind_non_integer_port() -> None:
    """A non-integer port is rejected."""
    with pytest.raises(ValueError, match="integer"):
        parse_bind("localhost:http")


def test_parse_bind_port_out_of_range() -> None:
    """A port outside ``0..65535`` is rejected."""
    with pytest.raises(ValueError, match="0..65535"):
        parse_bind("localhost:70000")


# --------------------------------------------------------------------------- #
# BearerTokenMiddleware                                                       #
# --------------------------------------------------------------------------- #
async def _echo_app(scope: dict, receive: object, send: object) -> None:
    """A minimal inner ASGI app echoing the current tenant as JSON."""
    body = json.dumps({"tenant": context_mod.current_tenant()}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _client(app: object) -> httpx.AsyncClient:
    """Build an ``AsyncClient`` speaking to ``app`` over ASGI."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.asyncio
async def test_bearer_rejects_missing_header() -> None:
    """A request with no ``Authorization`` header is rejected 401."""
    app = BearerTokenMiddleware(_echo_app, "s3cret")
    async with _client(app) as client:
        response = await client.get("/mcp")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_bearer_rejects_wrong_token() -> None:
    """A request with the wrong token is rejected 401."""
    app = BearerTokenMiddleware(_echo_app, "s3cret")
    async with _client(app) as client:
        response = await client.get(
            "/mcp", headers={"Authorization": "Bearer nope"}
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bearer_accepts_correct_token_and_forwards_tenant() -> None:
    """A correct token passes; the inner app sees the tenant header."""
    app = BearerTokenMiddleware(_echo_app, "s3cret")
    async with _client(app) as client:
        response = await client.get(
            "/mcp",
            headers={
                "Authorization": "Bearer s3cret",
                "X-MCP-Tenant": "acme",
            },
        )
    assert response.status_code == 200
    assert response.json() == {"tenant": "acme"}
    # The context variable is reset once the request completes.
    assert context_mod.current_tenant() is None


@pytest.mark.asyncio
async def test_bearer_passthrough_non_http() -> None:
    """A non-HTTP (e.g. lifespan) scope passes straight through."""
    seen: list[str] = []

    async def _inner(scope: dict, receive: object, send: object) -> None:
        seen.append(scope["type"])

    app = BearerTokenMiddleware(_inner, "s3cret")
    await app({"type": "lifespan"}, None, None)
    assert seen == ["lifespan"]


# --------------------------------------------------------------------------- #
# build_http_app                                                              #
# --------------------------------------------------------------------------- #
class _FakeServer:
    """A stand-in exposing ``streamable_http_app`` like FastMCP."""

    def streamable_http_app(self) -> object:
        """Return a sentinel inner ASGI app."""
        return _echo_app


def _oauth_config() -> oauth_mod.OAuthConfig:
    """A minimal OAuth config (no network is touched building it)."""
    return oauth_mod.OAuthConfig(
        issuer="https://auth.example.com",
        audience="https://mcp.example.com/mcp",
        jwks_url="https://auth.example.com/.well-known/jwks.json",
    )


def test_build_http_app_static_token() -> None:
    """A static token yields the ``BearerTokenMiddleware`` wrapper."""
    app = build_http_app(_FakeServer(), token="s3cret")
    assert isinstance(app, BearerTokenMiddleware)


def test_build_http_app_oauth() -> None:
    """An OAuth config yields the ``OAuthResourceMiddleware`` wrapper."""
    app = build_http_app(_FakeServer(), oauth_config=_oauth_config())
    assert isinstance(app, oauth_mod.OAuthResourceMiddleware)


def test_build_http_app_requires_auth() -> None:
    """Neither a token nor an OAuth config is a configuration error."""
    with pytest.raises(ValueError, match="static token or an OAuth config"):
        build_http_app(_FakeServer())


# --------------------------------------------------------------------------- #
# run_http                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture
def captured_uvicorn(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Capture ``uvicorn.run`` calls without starting a server."""
    calls: list[dict] = []
    monkeypatch.setattr(
        transport_mod.uvicorn,
        "run",
        lambda app, **kw: calls.append({"app": app, **kw}),
    )
    return calls


def test_run_http_oauth_path(
    monkeypatch: pytest.MonkeyPatch, captured_uvicorn: list[dict]
) -> None:
    """When OAuth is configured the OAuth app is served."""
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    monkeypatch.setattr(
        oauth_mod.OAuthConfig,
        "from_env",
        classmethod(lambda cls: _oauth_config()),
    )
    run_http(_FakeServer(), "127.0.0.1:8080")
    assert len(captured_uvicorn) == 1
    app = captured_uvicorn[0]["app"]
    assert isinstance(app, oauth_mod.OAuthResourceMiddleware)
    assert captured_uvicorn[0]["port"] == 8080


def test_run_http_oauth_warns_when_token_also_set(
    monkeypatch: pytest.MonkeyPatch,
    captured_uvicorn: list[dict],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A static token set alongside OAuth is ignored, with a warning."""
    monkeypatch.setenv(TOKEN_ENV, "ignored")
    monkeypatch.setattr(
        oauth_mod.OAuthConfig,
        "from_env",
        classmethod(lambda cls: _oauth_config()),
    )
    with caplog.at_level("WARNING"):
        run_http(_FakeServer(), "127.0.0.1:8080")
    assert "OAuth" in caplog.text and "IGNORED" in caplog.text
    assert isinstance(
        captured_uvicorn[0]["app"], oauth_mod.OAuthResourceMiddleware
    )


def test_run_http_static_token_path(
    monkeypatch: pytest.MonkeyPatch,
    captured_uvicorn: list[dict],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With no OAuth, the static dev-mode token is used, with a warning."""
    monkeypatch.setattr(
        oauth_mod.OAuthConfig, "from_env", classmethod(lambda cls: None)
    )
    monkeypatch.setenv(TOKEN_ENV, "s3cret")
    with caplog.at_level("WARNING"):
        run_http(_FakeServer(), "127.0.0.1:8080")
    assert "DEV-MODE" in caplog.text
    assert isinstance(captured_uvicorn[0]["app"], BearerTokenMiddleware)


def test_run_http_no_auth_exits(
    monkeypatch: pytest.MonkeyPatch, captured_uvicorn: list[dict]
) -> None:
    """Starting HTTP with neither OAuth nor a token is refused."""
    monkeypatch.setattr(
        oauth_mod.OAuthConfig, "from_env", classmethod(lambda cls: None)
    )
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    with pytest.raises(SystemExit, match="requires auth"):
        run_http(_FakeServer(), "127.0.0.1:8080")
    assert captured_uvicorn == []


def test_run_http_explicit_token_argument(
    monkeypatch: pytest.MonkeyPatch, captured_uvicorn: list[dict]
) -> None:
    """An explicit ``token`` argument is honoured over the environment."""
    monkeypatch.setattr(
        oauth_mod.OAuthConfig, "from_env", classmethod(lambda cls: None)
    )
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    run_http(_FakeServer(), "127.0.0.1:8080", token="explicit")
    assert isinstance(captured_uvicorn[0]["app"], BearerTokenMiddleware)


def test_run_http_bad_bind(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed bind is rejected before any auth resolution."""
    with pytest.raises(ValueError, match="HOST:PORT"):
        run_http(_FakeServer(), "nocolon")


def test_default_bind_is_loopback() -> None:
    """The default bind is loopback-only."""
    assert DEFAULT_BIND == "127.0.0.1:8080"
