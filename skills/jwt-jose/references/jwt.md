---
name: "JSON Web Token (JWT)"
description: "What a JWT is, claims set rules, registered/public/private claims, NumericDate, audience, explicit typing and token profiles, nested and unsecured JWTs, the complete validation checklist, lifetimes, revocation, and privacy (RFC 7519, RFC 9068, RFC 8725)."
tags: [jwt, rfc7519, rfc9068, rfc8725, claims, iss, sub, aud, exp, nbf, iat, jti, numericdate, typ, at+jwt, explicit-typing, id-token, access-token, nested-jwt, validation, leeway, revocation]
---

# JSON Web Token (JWT)

A JWT is a compact, URL-safe way to carry claims between two parties. The claims are a JSON object (the JWT Claims Set) that becomes the payload of a JWS or the plaintext of a JWE. In the source article's metaphor, the JWT is the letter; JWS and JWE are the envelope and the box. RFC 7519 suggests pronouncing it "jot".

## What Makes Something A JWT

- The payload is a JSON object of claims, UTF-8 encoded, with unique member names (reject duplicates).
- It is a JWS or JWE in the Compact Serialization. JSON serializations are never JWTs.
- "JWT" in conversation usually means a JWS whose payload is a claims set.

## Claim Categories

| Category | Definition | Example |
|---|---|---|
| Registered | Defined by RFC 7519 or registered with IANA. | `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti` |
| Public | Registered with IANA or collision-resistant (for example a URI you control). | `https://example.com/roles`, OIDC `auth_time`, `nonce`, `acr` |
| Private | Agreed between producer and consumer; may collide. | `tenant_id` |

IANA JWT claims registry: https://www.iana.org/assignments/jwt/jwt.xhtml

## Registered Claims

| Claim | Type | Meaning | Validation |
|---|---|---|---|
| `iss` | StringOrURI | Issuer | Exact string match against the trusted issuer, and the verifying key must belong to that issuer. |
| `sub` | StringOrURI | Subject | Must identify a valid subject for that issuer; unique per issuer, so key identity on (`iss`, `sub`). |
| `aud` | StringOrURI or array of them | Intended recipients | Reject if absent (when the issuer serves several audiences) or if none of the values is yours. |
| `exp` | NumericDate | Expiration | Reject when now is at or after `exp`, allowing small leeway. |
| `nbf` | NumericDate | Not before | Reject when now is before `nbf`, allowing small leeway. |
| `iat` | NumericDate | Issued at | Optional maximum-age check; reject far-future values. |
| `jti` | String | Unique token ID | Use for replay detection or revocation lists. |

All registered claims are optional in RFC 7519. Profiles make them mandatory: RFC 9068 access tokens require `iss`, `exp`, `aud`, `sub`, `client_id`, `iat`, and `jti`.

## NumericDate

- Seconds since 1970-01-01T00:00:00Z UTC, ignoring leap seconds. Non-integer values are allowed.
- Not milliseconds. JavaScript `Date.now()` returns milliseconds; divide by 1000 and floor.
- Leeway: RFC 7519 allows "some small leeway, usually no more than a few minutes" for clock skew. 30 to 60 seconds is common.

## Example Claims Sets

Access token (RFC 9068 shape):

```json
{
  "iss": "https://issuer.example.com/",
  "sub": "user-123",
  "aud": "https://api.example.com",
  "client_id": "s6BhdRkqt3",
  "scope": "read:messages",
  "iat": 1794500000,
  "exp": 1794500600,
  "jti": "9f8c2a6e-5d0b-4f8e-9a51-3c1d7b2e4a10"
}
```

with header:

```json
{"alg": "ES256", "kid": "es256-2026-11", "typ": "at+jwt"}
```

## Header Parameters For JWTs

| Parameter | Use |
|---|---|
| `typ` | RFC 7519 suggests `JWT` (uppercase). That is not explicit typing. For a new kind of token, register a media type `application/example+jwt` and set `typ` to `example+jwt`. Compare case-insensitively and treat a value without `/` as if `application/` were prepended. |
| `cty` | `JWT` when the payload is itself a JWT (nested JWT). Otherwise omit it. |

## Explicit Typing And Profiles

Different kinds of JWTs from the same issuer can look alike. An attacker who gets one kind (an ID token) can try to use it as another (an access token). Prevent this with explicit `typ` values and mutually exclusive validation rules.

| Token | `typ` | Defined by |
|---|---|---|
| OAuth 2.0 JWT access token | `at+jwt` | RFC 9068 (resource servers must reject other values) |
| Security Event Token | `secevent+jwt` | RFC 8417 |
| DPoP proof | `dpop+jwt` | RFC 9449 |
| OIDC back-channel logout token | `logout+jwt` | OpenID Connect Back-Channel Logout 1.0 |
| OIDC ID token | none mandated | OpenID Connect Core 1.0 |

Other ways to keep validation rules mutually exclusive (JWT BCP Section 3.12): different required claims, different `aud` values, different keys, or different issuers per token kind.

Audience by token type, as Auth0 documents it: an ID token's `aud` is the client ID of the application; an access token's `aud` is the API identifier. An API must reject ID tokens.

## Nested JWT

A nested JWT is a JWT used as the payload of another JWS or JWE. The usual form signs the claims (inner JWS) and then encrypts the JWS (outer JWE) with `"cty": "JWT"`. Put the explicit `typ` on the inner JWT. Validate both layers with keys and algorithms that the application chooses. See `references/jwe.md`.

## Unsecured JWT

An Unsecured JWT is a JWS with `"alg": "none"` and an empty signature:

```text
eyJhbGciOiJub25lIn0.eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFtcGxlLmNvbS9pc19yb290Ijp0cnVlfQ.
```

It proves nothing. Libraries must not accept it unless the caller explicitly allows it for that specific object. Deprecation of `none` is approved.

## Validating A JWT

Steps from RFC 7519 Section 7.2, the JWT BCP (RFC 8725 and its approved update), and RFC 9068, in order:

1. Check the format: only base64url characters and dots; 3 segments (JWS) or 5 (JWE). Reject anything else, including JSON serializations.
2. Decode the header; reject invalid UTF-8, invalid JSON, duplicate names, and unknown `crit` entries.
3. Decide the expected kind (JWS, JWE, or nested) from configuration, and reject a token of another kind.
4. Check `typ` against the expected explicit type when the profile has one.
5. Check `alg` (and `enc` for JWE) against the exact allowlist for this issuer. Never accept `none` unless explicitly configured for this object.
6. Resolve the key from trusted configuration or the issuer's JWKS, using `kid` as a lookup hint; confirm the key's type and `alg` match the token's `alg`.
7. Verify the signature (or decrypt and then verify the inner signature for nested JWTs). Any failure rejects the whole token.
8. Parse the claims; reject duplicate claim names.
9. Check `iss` equals the trusted issuer and that the key belongs to it.
10. Check `aud` contains your identifier.
11. Check `exp`, `nbf`, and optionally `iat` age, with small leeway.
12. Check profile-required claims (for example `sub`, `jti`, `client_id`, `scope`) and application authorization rules.
13. Treat every claim value as attacker-controlled input when you use it in lookups, queries, or URLs.

## Lifetimes, Refresh, And Revocation

- A signed JWT stays valid until `exp`; the issuer cannot recall it.
- Keep access token lifetimes short (minutes) and use refresh tokens or re-authentication for longer sessions.
- If you need revocation before `exp`, keep a denylist of `jti` values until their `exp`, or use opaque tokens with introspection.
- Key revocation (removing a key from the JWKS) invalidates every token signed with it once verifier caches expire.

## Privacy

- A JWS payload is readable by anyone holding the token: base64url is an encoding, not encryption.
- Put only the claims the recipient needs into the token. Use JWE when claims must stay confidential from the client or intermediaries.
- Avoid personal data in tokens that are logged, cached, or sent in URLs.

## Best Practices

- Use a maintained library and pass every expected value (algorithms, issuer, audience, type, required claims) explicitly.
- Require `exp`, `iss`, and `aud`, even though RFC 7519 makes them optional.
- Use explicit typing for every new kind of JWT.
- Read claims only from the verified result, never by splitting and decoding the string yourself.
- Keep tokens small and short-lived.
