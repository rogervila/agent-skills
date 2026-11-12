---
name: "Source Article: Demystifying JOSE"
description: "Attributed summary of the Auth0 article that maps the JOSE family (JOSE, JWS, JWE, JWA, JWK, JWKS, JWT) to a secure shipping metaphor, plus verified clarifications where the article simplifies or its samples are not usable."
tags: [jose, jwt, jws, jwe, jwa, jwk, jwks, auth0, metaphor, overview, compact-serialization, errata]
---

# Source Article: Demystifying JOSE

Source: Andrea Chiarelli, "Demystifying JOSE, the JWT Family: JWS, JWE, JWA, and JWK Explained", Auth0 blog, published 2025-10-07: https://auth0.com/blog/demystifying-jose-jwt-family/

This file is an original summary of the article for offline use, not a copy. The clarifications section records what was checked against the RFCs and by running code on 2026-11-12.

## The Core Idea

The JOSE acronyms are not competing technologies. They are parts of one system. The article explains them with a secure shipping company:

| Acronym | Full name | Role | Shipping metaphor | Is it a token? |
|---|---|---|---|---|
| JOSE | JSON Object Signing and Encryption | The framework: a set of IETF standards for securely transferring claims | The whole shipping company and its rules | No, a framework |
| JWS | JSON Web Signature | Integrity and authenticity through a signature or MAC | A clear envelope with a tamper-proof seal | Yes, a signed token |
| JWE | JSON Web Encryption | Confidentiality through encryption | A locked, opaque metal box | Yes, an encrypted token |
| JWA | JSON Web Algorithms | The registry of algorithm identifiers that JWS and JWE may use | The list of approved seal and lock types | No, a list of names |
| JWK | JSON Web Key | Keys represented as JSON | The actual key and its label | No, a key format |
| JWT | JSON Web Token | The structure of the claims inside the container | The letter inside the envelope or box | Yes, but always inside a JWS or JWE |

One-line recap from the article: JOSE is the framework; JWS and JWE are the containers; JWA and JWK are the tools; JWT is the content.

## Section Summaries

### JOSE

JOSE is not something you install. It is the umbrella for the IETF JOSE working group documents that define how to sign (JWS), encrypt (JWE), name algorithms (JWA), and represent keys (JWK). Document list: https://datatracker.ietf.org/wg/jose/documents/

### JWS

- Goals: integrity (the data was not changed) and authenticity (the sender is who it claims to be).
- A JWS does not hide its payload. Anyone can read it; the seal only proves origin and integrity.
- JWS Compact Serialization is three base64url parts joined by dots: header, payload, signature.
- The header carries metadata such as `"alg": "HS256"` and `"typ": "JWT"`. The payload carries the claims. The signature is computed over the encoded header and payload.
- JWS also has two JSON serializations: General (several signatures) and Flattened (one signature).

### JWE

- Goal: confidentiality. Only holders of the right key can read the content.
- JWE Compact Serialization has five base64url parts: protected header, encrypted key, initialization vector, ciphertext, authentication tag.
- If an algorithm uses no IV or no tag, that part is the empty octet sequence.
- JWE also has General and Flattened JSON serializations.

### JWA

JWA defines the algorithm identifiers that appear in headers: `HS256` (HMAC with SHA-256), `RS256` (RSA signature), `A256GCM` (AES-GCM content encryption), and so on. It is a specification and registry, not code.

### JWK And JWKS

- A JWK represents a key as JSON instead of PEM or DER files, with metadata: `kty` (key type such as `RSA` or `EC`), `use` (`sig` or `enc`), `kid` (key identifier), and the key values (for RSA: `n` and `e`).
- A JWK Set (JWKS) is a JSON object with a mandatory `keys` array of JWKs.
- Auth0 publishes each tenant's public keys at `https://<YOUR-DOMAIN>/.well-known/jwks.json`; applications fetch it to verify tokens.

### JWT

- A JWT is a set of claims, not a separate cryptographic technology. Registered claim names include `iss`, `sub`, `aud`, and `exp`.
- A JWT is secured by putting it in a JWS (signed, the common case) or a JWE (encrypted). A nested JWT is signed first and then encrypted.
- "Here is my JWT" almost always means a JWS whose payload is a JWT Claims Set.
- JWTs always use the Compact Serialization; the JSON serializations of JWS and JWE are not used for JWTs (RFC 7519 Section 1).

## Clarifications And Verified Errata

These points refine the article. Each was checked against the RFC text or by running code (see `references/verified-behavior.md`).

| Article statement or sample | Clarification | Evidence |
|---|---|---|
| The JWS sample token. | It is the jwt.io demo token. Its HS256 MAC verifies with the public secret `your-256-bit-secret`, which is 19 bytes. RFC 7518 Section 3.2 requires an HS256 key of at least 256 bits (32 bytes). Anyone can forge tokens with that secret. Never reuse it. | HMAC recomputed in Python and with `jose`; `firebase/php-jwt` 7.2.1 rejects the key as too short; PyJWT 2.15.1 warns. |
| The JWE sample token. | Illustrative only; it cannot be decrypted. The header says `RSA-OAEP` with `A256GCM`, but the IV is 16 bytes (A256GCM requires 96 bits, 12 bytes), and the encrypted key is 95 bytes (RSA-OAEP with a 2048-bit key gives 256 bytes). The header, IV, and last segment come from RFC 7516 examples; the last segment is the RFC 7516 A.3 symmetric key value. | `scripts/jose_inspect.py` reports `IV_LENGTH` and `RSA_KEY_TOO_SMALL`. |
| The JWKS sample. | It contains trailing commas, so it is not valid JSON. Copy keys from a real endpoint, not from the article. | `JSON.parse` rejects it. |
| "The JWE Encrypted Key ... is encrypted with the recipient's public key." | Only for key encryption algorithms (`RSA-OAEP`, `RSA-OAEP-256`). With `A128KW`/`A256KW` it is wrapped with a shared symmetric key. With `dir` and `ECDH-ES` (direct key agreement) the segment is empty. | RFC 7516 Sections 2 and 5.1 step 5; `jose` produces an empty segment for `dir` and `ECDH-ES`. |
| "Authenticity: verifies that the sender is who they claim to be." | True for digital signatures. With an HMAC algorithm (`HS256`), every party that can verify can also create tokens, so a MAC proves only that one of the key holders made it. | RFC 7515 Section 10.5. |
| "Signature: created by signing the encoded header and payload with a secret key." | The signing input is `ASCII(BASE64URL(UTF8(header)) || '.' || BASE64URL(payload))`. For HS* the key is a shared secret; for RS*, PS*, ES*, and Ed25519 it is a private key, verified with the public key. | RFC 7515 Section 5.1. |
| JWA as "a registry of identifiers". | RFC 7518 defines the algorithms and created the IANA registries. The registry keeps changing: RFC 9864 (October 2025) added `Ed25519`/`Ed448` and deprecated `EdDSA`; RFC 9964 (May 2026) added ML-DSA; deprecation of `none` and `RSA1_5` is approved and waiting in the RFC Editor queue. | IANA JOSE registry, updated 2026-09-29. |
| JWS and JWE as "tokens". | JWS and JWE can protect any payload, not only JWT claims. ACME (RFC 8555) requests, for example, are JWSs in the Flattened JSON Serialization. | RFC 7515 Section 1; RFC 8555 Section 6.2. |
| The JWK example lists `kty`, `use`, `kid`, `n`, `e`. | `use` may be replaced by `key_ops`; the two should not be used together. `alg` binds the key to one algorithm, which the JWT BCP now requires to be enforced. | RFC 7517 Sections 4.2-4.4; draft-ietf-oauth-rfc8725bis-10 Section 3.1. |
| Auth0's linked JWE doc shows `"alg": "A256GCM", "enc": "RSA-OAEP-256"`. | The values are swapped. `alg` is the key management algorithm (`RSA-OAEP-256`); `enc` is the content encryption algorithm (`A256GCM`). | RFC 7516 Sections 4.1.1-4.1.2. |

## Topics The Article Does Not Cover

Use the other references for these:

- Unsecured JWTs (`"alg": "none"`) and why libraries must reject them by default: `references/security-best-practices.md`.
- `typ` explicit typing, `cty`, `crit`, `kid` lookup, `jku`/`x5u`/`jwk`/`x5c` header risks: `references/jws.md`, `references/security-best-practices.md`.
- JWE key management modes and `epk`, `p2s`, `p2c`, `zip`: `references/jwe.md`.
- Claim validation rules (`exp`, `nbf`, `iat`, `aud`, `iss`, leeway): `references/jwt.md`.
- Key rotation, JWKS caching, thumbprints: `references/jwk.md`.

## Best Practices

- Use the metaphor to explain the family, then switch to precise terms: say "JWS" or "JWE" when the container matters.
- Treat the article's sample tokens and JWKS as illustrations. Use the RFC test vectors in `assets/test-vectors.json` when you need real ones.
- When the article and an RFC differ in detail, follow the RFC and say so.
