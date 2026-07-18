# HTTP transport & authentication

`iso20022-bank-profile-mcp` speaks **stdio by default** — one process per
operator, launched by the MCP client, with no network surface and no
authentication. That is the right shape for a local, single-operator
deployment and needs nothing from this page.

For **shared, multi-tenant deployments**, the server also offers an optional
streamable-HTTP transport. This page covers how to run it and how to
authenticate it.

## Running the HTTP transport

```sh
iso20022-bank-profile-mcp --transport=http --bind=127.0.0.1:8080
```

- `--transport` is `stdio` (default) or `http`.
- `--bind` takes a `HOST:PORT` string and defaults to `127.0.0.1:8080`
  (loopback-only). Exposing the server beyond the host is an explicit opt-in —
  bind to `0.0.0.0:8080` (or a specific interface) only once auth is in place.

The HTTP transport **refuses to start without authentication**: it never
serves an unauthenticated endpoint. Configure one of the two modes below.

## OAuth 2.1 resource server (RFC 9728)

The production mode. The server acts as an OAuth 2.1 **resource server**: it
validates the bearer JWTs your existing authorization server (Okta, Auth0,
Entra ID, …) issues. Running the authorization server itself is out of scope —
this server only validates the tokens it presents.

Set these environment variables:

| Variable | Required | Meaning |
| --- | --- | --- |
| `ISO20022_BANK_PROFILE_OAUTH_ISSUER` | **yes** | The authorization server's issuer identifier; the JWT `iss` claim must match it exactly. |
| `ISO20022_BANK_PROFILE_OAUTH_AUDIENCE` | **yes** | This server's canonical resource URI (RFC 8707); the JWT `aud` claim must contain it. |
| `ISO20022_BANK_PROFILE_OAUTH_JWKS_URL` | no | Where to fetch the JSON Web Key Set. Defaults to `<issuer>/.well-known/jwks.json`. |
| `ISO20022_BANK_PROFILE_OAUTH_SCOPES` | no | Space-separated scopes every token must carry. Unset / empty means no scope gate. |

Setting some but not both of `ISSUER` / `AUDIENCE` is a hard error — a
partial configuration fails loudly rather than serving with weaker auth.

```sh
ISO20022_BANK_PROFILE_OAUTH_ISSUER=https://auth.example.com \
ISO20022_BANK_PROFILE_OAUTH_AUDIENCE=https://mcp.example.com/mcp \
  iso20022-bank-profile-mcp --transport=http --bind=0.0.0.0:8080
```

### What is validated

Every HTTP request must present `Authorization: Bearer <jwt>`. The token is
checked, in order, for:

- a decodable structure and a signing key resolvable from the JWKS (the
  verification algorithm is taken from the JWKS key, never the token header,
  so `none` / HMAC downgrades are impossible with an asymmetric key set);
- a valid signature;
- `exp` and `nbf` (with a small clock-skew leeway);
- `iss` matching the configured issuer and `aud` containing the configured
  audience;
- every scope named in `ISO20022_BANK_PROFILE_OAUTH_SCOPES`.

Failures are rejected `401` (or `403` for `insufficient_scope`) with an
RFC 6750 / RFC 9728 `WWW-Authenticate` challenge that carries the
`resource_metadata` URL.

### Protected-resource metadata

The RFC 9728 protected-resource metadata document is served **unauthenticated**
on `GET` to `/.well-known/oauth-protected-resource` (and the audience-derived
variant). It advertises the `resource`, the `authorization_servers`, the
supported bearer methods, and — when configured — `scopes_supported`, so a
client can discover which authorization server to obtain a token from.

## Static dev-mode token

A fallback for local development only. Set `ISO20022_BANK_PROFILE_TOKEN` to a
shared secret:

```sh
ISO20022_BANK_PROFILE_TOKEN=s3cret \
  iso20022-bank-profile-mcp --transport=http --bind=127.0.0.1:8080
```

Every request must then send `Authorization: Bearer s3cret` (compared in
constant time). This is a single shared secret with **no expiry and no
scopes** — use OAuth 2.1 in production. If both OAuth and the static token are
configured, OAuth wins and the static token is ignored.

## Multi-tenancy

HTTP callers may send an optional `X-MCP-Tenant` header. It is forwarded into
the tool-visible request context for the duration of the request, so a
multi-tenant deployment can scope a call to a tenant/account. Under stdio the
tenant context is simply empty.

## Entitlements over HTTP

The OAuth token's scopes double as the **premium entitlement** mechanism:
a token bearing `profile:premium` is entitled to every premium profile, and a
token bearing `profile:<profile_id>` is entitled to just that one. Under stdio
the equivalent grant is the `ISO20022_BANK_PROFILE_ENTITLEMENTS` allowlist. See
[Clearing profiles → Entitlement & premium packs](profiles.md#entitlement-premium-packs)
for the full model.
