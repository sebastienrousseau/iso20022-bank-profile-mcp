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

"""OAuth 2.1 resource-server auth: JWKS, JWT validation, ASGI middleware.

JWTs are minted with a real RSA key pair; the JWKS is served either from an
injected cache (no network) or a fully faked ``httpx.AsyncClient``.
"""

from __future__ import annotations

import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from iso20022_bank_profile_mcp.http import context as context_mod
from iso20022_bank_profile_mcp.http import oauth as oauth_mod
from iso20022_bank_profile_mcp.http.oauth import (
    OAUTH_AUDIENCE_ENV,
    OAUTH_ISSUER_ENV,
    OAUTH_JWKS_URL_ENV,
    OAUTH_SCOPES_ENV,
    WELL_KNOWN_PATH,
    JWKSCache,
    JWTVerifier,
    OAuthConfig,
    OAuthResourceMiddleware,
    TokenValidationError,
    protected_resource_metadata,
    resource_metadata_url,
)

_ISSUER = "https://auth.example.com"
_AUDIENCE = "https://mcp.example.com/mcp"
_JWKS_URL = "https://auth.example.com/.well-known/jwks.json"


# --------------------------------------------------------------------------- #
# Key material (module-scoped: RSA generation is expensive)                  #
# --------------------------------------------------------------------------- #
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PEM = _OTHER_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)


def _jwk_entry(kid: str = "k1") -> dict:
    """Build a JWKS entry (public key) for the signing key pair."""
    entry = RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True)
    entry["kid"] = kid
    entry["use"] = "sig"
    return entry


def _config(required_scopes: tuple[str, ...] = ()) -> OAuthConfig:
    """A resource-server config for the test issuer/audience."""
    return OAuthConfig(
        issuer=_ISSUER,
        audience=_AUDIENCE,
        jwks_url=_JWKS_URL,
        required_scopes=required_scopes,
    )


def _cache_with_key() -> JWKSCache:
    """A JWKS cache pre-seeded with the signing key (never fetches)."""
    cache = JWKSCache(_JWKS_URL)
    cache._keys = {"k1": jwt.PyJWK(_jwk_entry())}
    cache._fetched_at = float("inf")
    return cache


def _make_token(
    overrides: dict | None = None,
    *,
    headers: dict | None = None,
    pem: bytes | None = None,
) -> str:
    """Sign a JWT with sensible defaults, applying ``overrides``."""
    now = int(time.time())
    claims: dict = {
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "exp": now + 3600,
        "iat": now,
        "sub": "user-1",
        "scope": "",
    }
    if overrides:
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(
        claims,
        pem or _PRIVATE_PEM,
        algorithm="RS256",
        headers=headers or {"kid": "k1"},
    )


def _verifier(config: OAuthConfig | None = None) -> JWTVerifier:
    """A verifier over the pre-seeded cache."""
    return JWTVerifier(config or _config(), jwks=_cache_with_key())


# --------------------------------------------------------------------------- #
# JWTVerifier.verify: reason codes                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_verify_valid_token() -> None:
    """A well-formed token yields an AccessToken with scopes and subject."""
    token = _make_token({"scope": "a b", "client_id": "client-42"})
    access = await _verifier().verify(token)
    assert access.client_id == "client-42"
    assert access.scopes == ["a", "b"]
    assert access.subject == "user-1"
    assert access.resource == _AUDIENCE


@pytest.mark.asyncio
async def test_verify_expired() -> None:
    """An expired token reports ``token_expired``."""
    now = int(time.time())
    token = _make_token({"exp": now - 3600, "iat": now - 7200})
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify(token)
    assert info.value.reason == "token_expired"


@pytest.mark.asyncio
async def test_verify_not_yet_valid() -> None:
    """A token whose ``nbf`` is in the future reports not-yet-valid."""
    token = _make_token({"nbf": int(time.time()) + 3600})
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify(token)
    assert info.value.reason == "token_not_yet_valid"


@pytest.mark.asyncio
async def test_verify_wrong_issuer() -> None:
    """A mismatched ``iss`` reports ``issuer_mismatch``."""
    token = _make_token({"iss": "https://evil.example.com"})
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify(token)
    assert info.value.reason == "issuer_mismatch"


@pytest.mark.asyncio
async def test_verify_wrong_audience() -> None:
    """A mismatched ``aud`` reports ``audience_mismatch``."""
    token = _make_token({"aud": "https://other.example.com"})
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify(token)
    assert info.value.reason == "audience_mismatch"


@pytest.mark.asyncio
async def test_verify_bad_signature() -> None:
    """A token signed by a different key reports ``signature_invalid``."""
    token = _make_token(pem=_OTHER_PEM)
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify(token)
    assert info.value.reason == "signature_invalid"


@pytest.mark.asyncio
async def test_verify_malformed_token() -> None:
    """A non-decodable token reports ``malformed_token``."""
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify("not-a-jwt")
    assert info.value.reason == "malformed_token"


@pytest.mark.asyncio
async def test_verify_missing_required_claim() -> None:
    """A token missing a required claim reports ``missing_required_claim``."""
    token = _make_token({"exp": None})  # drop exp entirely
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify(token)
    assert info.value.reason == "missing_required_claim"


@pytest.mark.asyncio
async def test_verify_generic_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unmapped ``InvalidTokenError`` falls back to ``invalid_token``."""

    def _boom(*args: object, **kwargs: object) -> None:
        raise jwt.exceptions.InvalidTokenError("weird")

    monkeypatch.setattr(oauth_mod.jwt, "decode", _boom)
    with pytest.raises(TokenValidationError) as info:
        await _verifier().verify(_make_token())
    assert info.value.reason == "invalid_token"


@pytest.mark.asyncio
async def test_verify_insufficient_scope() -> None:
    """A token lacking a required scope reports ``insufficient_scope``."""
    verifier = _verifier(_config(required_scopes=("bank-profile:read",)))
    with pytest.raises(TokenValidationError) as info:
        await verifier.verify(_make_token({"scope": "something-else"}))
    assert info.value.reason == "insufficient_scope"


@pytest.mark.asyncio
async def test_verify_required_scope_present() -> None:
    """A token carrying every required scope validates."""
    verifier = _verifier(_config(required_scopes=("bank-profile:read",)))
    access = await verifier.verify(
        _make_token({"scope": "bank-profile:read extra"})
    )
    assert "bank-profile:read" in access.scopes


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"client_id": "cid", "azp": "azp", "sub": "sub"}, "cid"),
        ({"client_id": None, "azp": "azp", "sub": "sub"}, "azp"),
        ({"client_id": None, "azp": None, "sub": "sub"}, "sub"),
    ],
)
async def test_verify_client_id_precedence(
    overrides: dict, expected: str
) -> None:
    """``client_id`` prefers ``client_id`` then ``azp`` then ``sub``."""
    access = await _verifier().verify(_make_token(overrides))
    assert access.client_id == expected


@pytest.mark.asyncio
async def test_verify_token_returns_none_on_failure() -> None:
    """``verify_token`` returns ``None`` instead of raising."""
    now = int(time.time())
    expired = _make_token({"exp": now - 3600, "iat": now - 7200})
    assert await _verifier().verify_token(expired) is None


@pytest.mark.asyncio
async def test_verify_token_returns_access_on_success() -> None:
    """``verify_token`` returns the AccessToken on success."""
    access = await _verifier().verify_token(_make_token())
    assert access is not None
    assert access.subject == "user-1"


# --------------------------------------------------------------------------- #
# JWKSCache.get_key                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_key_cached_kid() -> None:
    """A known, cached ``kid`` resolves without a refresh."""
    cache = _cache_with_key()
    assert (await cache.get_key("k1")).algorithm_name == "RS256"


@pytest.mark.asyncio
async def test_get_key_none_kid_single_key() -> None:
    """A ``None`` kid resolves when the key set holds exactly one key."""
    cache = _cache_with_key()
    assert (await cache.get_key(None)).algorithm_name == "RS256"


@pytest.mark.asyncio
async def test_get_key_none_kid_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ``None`` kid with an ambiguous key set reports ``missing_kid``."""
    cache = _cache_with_key()
    cache._keys["k2"] = jwt.PyJWK(_jwk_entry("k2"))
    with pytest.raises(TokenValidationError) as info:
        await cache.get_key(None)
    assert info.value.reason == "missing_kid"


@pytest.mark.asyncio
async def test_get_key_unknown_kid(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown ``kid`` (even after a refresh) reports ``unknown_kid``."""
    cache = _cache_with_key()

    async def _noop() -> None:
        return None

    monkeypatch.setattr(cache, "_refresh", _noop)
    with pytest.raises(TokenValidationError) as info:
        await cache.get_key("nope")
    assert info.value.reason == "unknown_kid"


@pytest.mark.asyncio
async def test_get_key_stale_triggers_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale cache refreshes before resolving the key."""
    cache = JWKSCache(_JWKS_URL)
    cache._fetched_at = float("-inf")  # force stale
    refreshed: list[bool] = []

    async def _refresh() -> None:
        refreshed.append(True)
        cache._keys = {"k1": jwt.PyJWK(_jwk_entry())}
        cache._fetched_at = float("inf")

    monkeypatch.setattr(cache, "_refresh", _refresh)
    assert (await cache.get_key("k1")).algorithm_name == "RS256"
    assert refreshed == [True]


# --------------------------------------------------------------------------- #
# JWKSCache._refresh (faked httpx.AsyncClient)                               #
# --------------------------------------------------------------------------- #
def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    payload: object = None,
    raise_status: Exception | None = None,
    get_error: Exception | None = None,
) -> None:
    """Replace ``oauth.httpx.AsyncClient`` with a fully local fake."""

    class _Resp:
        def raise_for_status(self) -> None:
            if raise_status is not None:
                raise raise_status

        def json(self) -> object:
            return payload

    class _Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def get(self, url: str) -> _Resp:
            if get_error is not None:
                raise get_error
            return _Resp()

    monkeypatch.setattr(oauth_mod.httpx, "AsyncClient", _Client)


@pytest.mark.asyncio
async def test_refresh_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid JWKS document populates the key index."""
    _install_fake_client(monkeypatch, payload={"keys": [_jwk_entry()]})
    cache = JWKSCache(_JWKS_URL)
    await cache._refresh()
    assert "k1" in cache._keys


@pytest.mark.asyncio
async def test_refresh_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """An HTTP error surfaces as ``jwks_unavailable``."""
    _install_fake_client(monkeypatch, raise_status=httpx.HTTPError("boom"))
    cache = JWKSCache(_JWKS_URL)
    with pytest.raises(TokenValidationError) as info:
        await cache._refresh()
    assert info.value.reason == "jwks_unavailable"


@pytest.mark.asyncio
async def test_refresh_missing_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A document without ``keys`` (KeyError) is ``jwks_unavailable``."""
    _install_fake_client(monkeypatch, payload={})
    with pytest.raises(TokenValidationError) as info:
        await JWKSCache(_JWKS_URL)._refresh()
    assert info.value.reason == "jwks_unavailable"


@pytest.mark.asyncio
async def test_refresh_keys_not_a_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-list ``keys`` member (TypeError) is ``jwks_unavailable``."""
    _install_fake_client(monkeypatch, payload={"keys": "nope"})
    with pytest.raises(TokenValidationError) as info:
        await JWKSCache(_JWKS_URL)._refresh()
    assert info.value.reason == "jwks_unavailable"


@pytest.mark.asyncio
async def test_refresh_skips_entry_without_kid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An entry lacking a ``kid`` is skipped; good entries are kept."""
    _install_fake_client(
        monkeypatch,
        payload={"keys": [{"kty": "RSA"}, _jwk_entry()]},
    )
    cache = JWKSCache(_JWKS_URL)
    await cache._refresh()
    assert list(cache._keys) == ["k1"]


@pytest.mark.asyncio
async def test_refresh_skips_unusable_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unusable JWK entry is skipped; good entries are kept."""
    _install_fake_client(
        monkeypatch,
        payload={"keys": [{"kid": "bad", "kty": "RSA"}, _jwk_entry()]},
    )
    cache = JWKSCache(_JWKS_URL)
    await cache._refresh()
    assert list(cache._keys) == ["k1"]


# --------------------------------------------------------------------------- #
# OAuthResourceMiddleware (ASGI end-to-end)                                  #
# --------------------------------------------------------------------------- #
async def _inner_app(scope: dict, receive: object, send: object) -> None:
    """Inner ASGI app echoing the authenticated tenant and scopes."""
    body = json.dumps(
        {
            "tenant": context_mod.current_tenant(),
            "scopes": list(context_mod.current_scopes()),
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _middleware(config: OAuthConfig | None = None) -> OAuthResourceMiddleware:
    """A middleware wrapping ``_inner_app`` with the pre-seeded verifier."""
    config = config or _config()
    return OAuthResourceMiddleware(_inner_app, _verifier(config), config)


def _client(app: object) -> httpx.AsyncClient:
    """An ``AsyncClient`` speaking to ``app`` over ASGI."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        WELL_KNOWN_PATH,
        "/.well-known/oauth-protected-resource/mcp",
    ],
)
async def test_metadata_served_unauthenticated(path: str) -> None:
    """Both metadata paths are served without auth on GET."""
    async with _client(_middleware()) as client:
        response = await client.get(path)
    assert response.status_code == 200
    body = response.json()
    assert body["resource"] == _AUDIENCE
    assert body["authorization_servers"] == [_ISSUER]


@pytest.mark.asyncio
async def test_missing_bearer_rejected_401() -> None:
    """A request with no bearer token is rejected 401 with a challenge."""
    async with _client(_middleware()) as client:
        response = await client.get("/mcp")
    assert response.status_code == 401
    assert "resource_metadata=" in response.headers["WWW-Authenticate"]


@pytest.mark.asyncio
async def test_invalid_bearer_rejected_401() -> None:
    """A request with an undecodable token is rejected 401."""
    async with _client(_middleware()) as client:
        response = await client.get(
            "/mcp", headers={"Authorization": "Bearer garbage"}
        )
    assert response.status_code == 401
    assert 'error="invalid_token"' in response.headers["WWW-Authenticate"]


@pytest.mark.asyncio
async def test_insufficient_scope_rejected_403() -> None:
    """A token lacking a required scope is rejected 403."""
    middleware = _middleware(_config(required_scopes=("bank-profile:read",)))
    async with _client(middleware) as client:
        response = await client.get(
            "/mcp",
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
    assert response.status_code == 403
    assert 'error="insufficient_scope"' in response.headers["WWW-Authenticate"]


@pytest.mark.asyncio
async def test_valid_token_forwards_context() -> None:
    """A valid token passes; the inner app sees the tenant and scopes."""
    token = _make_token({"scope": "profile:premium"})
    async with _client(_middleware()) as client:
        response = await client.get(
            "/mcp",
            headers={
                "Authorization": f"Bearer {token}",
                "X-MCP-Tenant": "acme",
            },
        )
    assert response.status_code == 200
    assert response.json() == {
        "tenant": "acme",
        "scopes": ["profile:premium"],
    }
    # Context is reset after the request.
    assert context_mod.current_tenant() is None
    assert context_mod.current_scopes() == ()


@pytest.mark.asyncio
async def test_middleware_passthrough_non_http() -> None:
    """A non-HTTP scope passes straight through to the inner app."""
    seen: list[str] = []

    async def _inner(scope: dict, receive: object, send: object) -> None:
        seen.append(scope["type"])

    middleware = OAuthResourceMiddleware(_inner, _verifier(), _config())
    await middleware({"type": "lifespan"}, None, None)
    assert seen == ["lifespan"]


# --------------------------------------------------------------------------- #
# OAuthConfig.from_env                                                       #
# --------------------------------------------------------------------------- #
def test_from_env_empty_returns_none() -> None:
    """No OAuth variables set yields ``None`` (dev-token fallback)."""
    assert OAuthConfig.from_env({}) is None


def test_from_env_partial_exits() -> None:
    """A partial configuration fails loudly with ``SystemExit``."""
    with pytest.raises(SystemExit):
        OAuthConfig.from_env({OAUTH_ISSUER_ENV: _ISSUER})


def test_from_env_full_defaults_jwks() -> None:
    """Issuer + audience derive the default JWKS URL when none is given."""
    config = OAuthConfig.from_env(
        {OAUTH_ISSUER_ENV: _ISSUER, OAUTH_AUDIENCE_ENV: _AUDIENCE}
    )
    assert config is not None
    assert config.jwks_url == _JWKS_URL
    assert config.required_scopes == ()


def test_from_env_explicit_jwks_and_scopes() -> None:
    """Explicit JWKS URL and scopes are carried through."""
    config = OAuthConfig.from_env(
        {
            OAUTH_ISSUER_ENV: _ISSUER,
            OAUTH_AUDIENCE_ENV: _AUDIENCE,
            OAUTH_JWKS_URL_ENV: "https://keys.example.com/jwks",
            OAUTH_SCOPES_ENV: "read write",
        }
    )
    assert config is not None
    assert config.jwks_url == "https://keys.example.com/jwks"
    assert config.required_scopes == ("read", "write")


# --------------------------------------------------------------------------- #
# metadata helpers                                                           #
# --------------------------------------------------------------------------- #
def test_protected_resource_metadata_without_scopes() -> None:
    """Metadata omits ``scopes_supported`` when no scopes are required."""
    metadata = protected_resource_metadata(_config())
    assert "scopes_supported" not in metadata
    assert metadata["bearer_methods_supported"] == ["header"]


def test_protected_resource_metadata_with_scopes() -> None:
    """Metadata lists ``scopes_supported`` when scopes are required."""
    metadata = protected_resource_metadata(_config(required_scopes=("read",)))
    assert metadata["scopes_supported"] == ["read"]


def test_resource_metadata_url_with_path() -> None:
    """A resource with a path nests it after the well-known segment."""
    assert (
        resource_metadata_url(_AUDIENCE)
        == "https://mcp.example.com/.well-known/oauth-protected-resource/mcp"
    )


def test_resource_metadata_url_bare_origin() -> None:
    """A bare-origin resource yields the well-known path with no suffix."""
    assert (
        resource_metadata_url("https://mcp.example.com")
        == "https://mcp.example.com/.well-known/oauth-protected-resource"
    )
    # A single trailing slash is treated as no path.
    assert (
        resource_metadata_url("https://mcp.example.com/")
        == "https://mcp.example.com/.well-known/oauth-protected-resource"
    )
