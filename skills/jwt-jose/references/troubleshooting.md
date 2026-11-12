---
name: "JWT And JOSE Troubleshooting"
description: "Diagnosis table for common JWT and JOSE failures (malformed token, invalid signature, unknown kid, expired, invalid audience or issuer, JWE decryption errors, unsupported algorithms, oversized tokens) and a safe step-by-step debugging workflow."
tags: [troubleshooting, debugging, invalid-signature, jwt-malformed, kid-not-found, jwks, expired, clock-skew, invalid-audience, invalid-issuer, opaque-token, jwe-decryption, base64url, auth0]
---

# JWT And JOSE Troubleshooting

## Safe Debugging Workflow

1. Do not paste production tokens or keys into websites, tickets, or chat. Decode locally: `python scripts/jose_inspect.py token -` (reads stdin, never verifies or decrypts, never prints signatures or private key members).
2. Count the segments: 3 is a JWS, 5 is a JWE, anything else is not a compact JOSE object (maybe an opaque token).
3. Compare the decoded header and claims with configuration: `alg`, `kid`, `typ`, `iss`, `aud`, `exp`.
4. Fetch the issuer's JWKS from configuration and check that a key with that `kid` exists and fits `alg`: `python scripts/jose_inspect.py jwk jwks.json`.
5. Check the server clock (NTP) against `exp`, `nbf`, and `iat`.
6. Reproduce with the project's verification function in a unit test, including the failing token's shape with a test key.
7. Fix the configuration or code; never "fix" by disabling verification or widening allowlists.

## Diagnosis Table

| Symptom (typical message) | Likely causes | Checks and fixes |
|---|---|---|
| Malformed token, wrong number of segments, invalid compact JWS | `Bearer ` prefix or quotes included; token URL-encoded or truncated; a JWE (5 parts) sent to a JWS verifier; an opaque access token; a JSON serialization. | Strip the scheme; count dots; check for `%2E` or `=`; confirm which token the client sends. |
| Not a JWT at all, a short random string | Opaque token. Auth0, for example, issues an opaque access token for `/userinfo` when no `audience` is requested. | Request the token with the API's `audience`, or validate opaque tokens through introspection or the issuer's endpoint. |
| Invalid signature | Wrong key (other tenant, environment, or rotated key); HMAC secret encoded differently (base64-decoded bytes versus the literal string); payload or header modified, re-serialized, or trimmed; ECDSA signature in DER instead of `R || S`; verifying with the wrong key type. | Match `kid` to the JWKS; confirm the secret's byte form; verify the exact received string; check signature length with the inspector. |
| No matching key, `kid` not found | Key rotated and cache stale; wrong JWKS URL (custom domain versus default domain, staging versus production); token from another issuer; JWKS has several keys and the token has no `kid`. | Refetch JWKS once on unknown `kid`; derive the JWKS URL from the trusted issuer's metadata; require `kid` when the set has several keys. |
| Algorithm not allowed or unsupported | Issuer changed algorithm (RS256 to PS256 or ES256); `EdDSA` versus `Ed25519` naming; library lacks ES256K or ML-DSA; `alg: none` sent by an attacker. | Update the allowlist deliberately after confirming the issuer change; never add `none`. |
| Expired (`exp`) or not yet valid (`nbf`, `iat` in the future) | Clock skew; timestamps in milliseconds; token cached by the client past its lifetime; very short lifetime. | Sync clocks; allow 30-60 seconds of leeway; check `exp` is in seconds; refresh tokens before expiry. |
| Invalid audience | Token issued for another API; an ID token (audience = client ID) sent to an API that expects an access token (audience = API identifier); `aud` is an array and the code compares with a string; trailing slash or scheme differences. | Request the token for the right audience; reject ID tokens at APIs; check array membership; compare exact strings. |
| Invalid issuer | Custom domain versus default domain; `http` versus `https`; trailing slash differences; multi-tenant issuer templates. | Configure the exact `iss` string the issuer publishes in its discovery metadata. |
| Unexpected `typ` | An ID token or other JWT kind sent where `at+jwt` is required; the issuer does not set `typ`. | Send the access token, not the ID token; if the issuer cannot set `typ`, use other mutually exclusive rules (audience, required claims) and document it. |
| Missing required claim | The issuer omits `jti`, `sub`, `client_id`, or `scope`; wrong token type. | Align the profile with the issuer; do not drop requirements silently. |
| JWE decryption fails | Wrong private key or `kid`; `alg` or `enc` not allowlisted; header changed in transit (it is the AAD); truncated ciphertext; `dir` key size does not match `enc`; PBES2 `p2c` above the cap. | Inspect segment sizes; check the key's `use: enc` and `alg`; return one generic error to clients but log the detail internally. |
| Decryption works but the token is still rejected | Inner JWS signature invalid or from an unknown key; inner `typ` wrong. | Expected behavior for forged nested tokens; verify the inner token like any JWS. |
| Request headers too large | Many claims or long group lists; nested JWE plus large signatures (ML-DSA signatures are 2.4-4.6 KB). | Keep claims minimal; reference large data by ID; prefer ES256 or Ed25519 for small tokens. |
| Works locally, fails in production | Different issuer, audience, JWKS URL, or clock; JWKS endpoint blocked by egress rules. | Log the configuration values (not secrets) at startup; health-check the JWKS fetch. |

## Encoding Pitfalls

- Base64url uses `-` and `_` and no padding. Standard base64 (`+`, `/`, `=`) is invalid in compact JOSE, except inside `x5c`, which is standard base64.
- JSON in headers and claims must be UTF-8.
- Do not re-serialize decoded JSON and then verify; the signature covers the original bytes.
- HMAC keys are bytes. Decide once whether the configured secret is raw text or base64-encoded bytes, and document it.

## Best Practices

- Debug with local, read-only tools and redacted logs.
- Reproduce failures as unit tests before changing code.
- Fix configuration mismatches at the source (issuer metadata, audience request) rather than relaxing validation.
- Keep a runbook entry for key rotation and JWKS cache behavior.
