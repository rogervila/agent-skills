---
name: "JSON Web Key (JWK) And JWK Sets"
description: "JWK members per key type, use versus key_ops, JWK Sets and JWKS endpoints, discovery, caching and key rotation, kid strategies, RFC 7638 thumbprints, private key protection, and certificate members (RFC 7517, RFC 7518, RFC 7638, RFC 9278)."
tags: [jwk, jwks, rfc7517, rfc7638, rfc9278, kid, kty, use, key_ops, thumbprint, key-rotation, jwks_uri, caching, x5c, private-key, public-key, oct, rsa, ec, okp, akp]
---

# JSON Web Key (JWK) And JWK Sets

A JWK is a key as a JSON object. A JWK Set is a JSON object with a `keys` array. In the source article's metaphor the JWK is the physical key with its label.

## Common Members

| Member | Meaning | Notes |
|---|---|---|
| `kty` | Key type: `RSA`, `EC`, `oct`, `OKP`, `AKP`. | Required. Case-sensitive. |
| `use` | Public key use: `sig` or `enc`. | For public keys. |
| `key_ops` | Allowed operations: `sign`, `verify`, `encrypt`, `decrypt`, `wrapKey`, `unwrapKey`, `deriveKey`, `deriveBits`. | Do not combine with `use`; if both appear they must agree (RFC 7517 Section 4.3). |
| `alg` | The one algorithm this key is for. | The JWT BCP update requires each key to be used with exactly one algorithm. |
| `kid` | Key identifier, case-sensitive string. | Keys in one set should have distinct `kid` values. |
| `x5u`, `x5c`, `x5t`, `x5t#S256` | Certificate URL, chain (standard base64 DER, key certificate first), SHA-1 and SHA-256 thumbprints. | The certificate key must match the JWK key. |

Unknown members must be ignored. Duplicate member names must be rejected or resolved to the last one.

## Members Per Key Type

| `kty` | Public members | Private members | Notes |
|---|---|---|---|
| `RSA` | `n` (modulus), `e` (exponent) | `d`, `p`, `q`, `dp`, `dq`, `qi`, `oth` | Base64urlUInt: big-endian, minimum number of octets. `e` is usually `AQAB` (65537). |
| `EC` | `crv`, `x`, `y` | `d` | `x`, `y`, `d` are full-length: 32 bytes for P-256, 48 for P-384, 66 for P-521. |
| `oct` | none | `k` | The whole key is secret. Never publish it. |
| `OKP` | `crv`, `x` | `d` | `Ed25519` (32 bytes), `Ed448` (57), `X25519` (32), `X448` (56). |
| `AKP` | `alg`, `pub` | `priv` (32-byte seed) | ML-DSA (RFC 9964). |

## JWK Set

RFC 7517 Appendix A.1 public keys, a valid JWK Set:

```json
{
  "keys": [
    {
      "kty": "EC",
      "crv": "P-256",
      "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
      "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
      "use": "enc",
      "kid": "1"
    },
    {
      "kty": "RSA",
      "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
      "e": "AQAB",
      "alg": "RS256",
      "kid": "2011-04-29"
    }
  ]
}
```

Rules:

- `keys` is required and is an array.
- Recipients should ignore keys with an unknown `kty`, missing required members, or unsupported values, instead of failing the whole set.
- Media types: `application/jwk+json` for one key, `application/jwk-set+json` for a set.

## Publishing A JWKS Endpoint

- Publish only public keys. A JWKS that contains `d`, `p`, `q`, `dp`, `dq`, `qi`, `oth`, `k`, or `priv` leaks signing or decryption keys. Check with `python scripts/jose_inspect.py jwk jwks.json`.
- Serve it over HTTPS. Discovery documents point to it: `jwks_uri` in OAuth 2.0 Authorization Server Metadata (RFC 8414) and OpenID Connect Discovery.
- Common location: `https://<issuer>/.well-known/jwks.json` (Auth0 uses this for each tenant).
- Give every key a stable, unique `kid`, plus `alg` and `use`.
- Set HTTP caching headers that match your rotation schedule.

## Consuming A JWKS

1. Get the JWKS URL from configuration or the issuer's discovery metadata, never from the token (`jku`, `x5u`).
2. Cache the set. Auth0 suggests 5 to 10 minutes when you implement caching yourself, but prefer a library that does it.
3. On an unknown `kid`, refetch once, then rate-limit further refetches so attackers cannot flood the endpoint with random `kid` values.
4. Match keys by `kid`, then confirm `kty`, `alg`, and `use` fit the token's `alg`.
5. Keep serving cached keys if the endpoint is briefly down, but stop accepting a key once it is removed and the cache expires.

## Key Rotation

1. Generate the new key and add it to the JWKS, while still signing with the old key.
2. Wait at least the longest verifier cache lifetime.
3. Start signing with the new key (new `kid`).
4. Keep the old public key in the JWKS until every token signed with it has expired.
5. Remove the old key. For an emergency revocation, remove it at once and accept that tokens signed with it will fail.

Auth0 signs with one key at a time but warns that its JWKS can hold several keys during rotation; verifiers must handle multiple keys.

## Choosing `kid` Values

- The RFC 7638 thumbprint of the public key is a good `kid`: it is unique, derived from the key, and the same for the public and private JWK.
- Otherwise use an opaque, unique string such as `es256-2026-11`.
- Do not encode file paths, database queries, or URLs in `kid`.

## JWK Thumbprint (RFC 7638)

1. Take only the required public members for the key type.
2. Order them lexicographically by member name.
3. Serialize as JSON with no whitespace.
4. Hash the UTF-8 bytes with SHA-256 and base64url-encode the hash.

| `kty` | Members, in order |
|---|---|
| `RSA` | `e`, `kty`, `n` |
| `EC` | `crv`, `kty`, `x`, `y` |
| `oct` | `k`, `kty` |
| `OKP` | `crv`, `kty`, `x` |
| `AKP` | `alg`, `kty`, `pub` |

RFC 7638 example: the RFC 7517 RSA key above has the thumbprint `NzbLsXh8uDCcd-6MNwXF4W_7noWXFZAfHkxZsRGC9Xs`. As a URI (RFC 9278): `urn:ietf:params:oauth:jwk-thumbprint:sha-256:NzbLsXh8uDCcd-6MNwXF4W_7noWXFZAfHkxZsRGC9Xs`.

Pitfall: hashing the whole JWK (with `alg`, `kid`, `use`) gives a different value. In joserfc 1.8.0, `jwk.thumbprint(dict)` hashes every member it is given, while `Key.thumbprint()` selects the required members. See `references/verified-behavior.md`.

## Protecting Private JWKs

- Store private JWKs in a secrets manager, KMS, or HSM rather than in source code or environment files where possible.
- If a private JWK must be stored or sent, encrypt it as a JWE with `cty` `jwk+json` (or `jwk-set+json` for sets), as RFC 7517 Section 7 describes.
- Never log private JWKs. `scripts/jose_inspect.py` never prints private members.

## Converting Keys

Libraries convert between PEM, DER, and JWK. Examples: `exportJWK` and `importJWK` in `jose` (JavaScript), `jwt.algorithms.RSAAlgorithm.to_jwk` and `PyJWK` in PyJWT, `RSAKey.import_key` in joserfc, `JWKFactory::createFromKey` in web-token (PHP). Avoid hand-written conversions; the Base64urlUInt and fixed-length EC coordinate rules are easy to get wrong.

## Best Practices

- One key, one algorithm, one purpose: set `alg` and `use` and enforce them.
- Keep signing keys and encryption keys separate.
- Publish only public keys and lint the JWKS before every deployment.
- Rotate on a schedule and overlap old and new keys for at least the token lifetime plus the cache lifetime.
- Use RFC 7638 thumbprints as `kid` values when you have no other naming scheme.
