---
name: "JWT And JOSE Security Best Practices"
description: "Threats against JWT and JOSE implementations and their mitigations, following RFC 8725 and its approved update draft-ietf-oauth-rfc8725bis-10, with known CVE examples, a review checklist, and operational rules for keys, logging, and token handling."
tags: [security, rfc8725, bcp225, rfc8725bis, alg-none, algorithm-confusion, key-confusion, kid-injection, jku, ssrf, embedded-jwk, invalid-curve, pbes2, decompression-bomb, format-confusion, cross-jwt-confusion, substitution, weak-secret, cve]
---

# JWT And JOSE Security Best Practices

RFC 8725 (BCP 225) is the published JWT Best Current Practice. Its update, draft-ietf-oauth-rfc8725bis revision -10, is approved and in the RFC Editor queue (checked 2026-11-12); it keeps all RFC 8725 guidance and adds rules for attacks found since 2020. Section numbers below refer to the update.

## Threats And Mitigations

| Threat | What goes wrong | Mitigation |
|---|---|---|
| `alg: none` (2.1) | The attacker sets `alg` to `none`, removes the signature, and a library "validates" it. | Allowlist algorithms per issuer and key; libraries must not accept `none` unless the caller explicitly allows it (3.1, 3.2). |
| Algorithm confusion (2.1) | A token switched from `RS256` to `HS256` is MACed with the RSA public key, and a library uses that public key as the HMAC secret (CVE-2015-9235). | Bind each key to one algorithm and key type; verify with key objects, not raw strings; allowlist `alg` (3.1). |
| Case variants (2.11) | A blocklist rejects `none` but the parser reads `noNE` case-insensitively. | Exact-match allowlists. Algorithm names are case-sensitive (3.1). |
| Weak HMAC keys (2.2) | Passwords or short strings as HS256 keys fall to offline brute force once one token leaks. | Random keys of at least the hash size (32 bytes for HS256); never a human-memorable password (3.5). |
| Decryption mistaken for authentication (2.3) | A library returns "valid" after decrypting a JWE that anyone could have created with the public key (CVE-2023-51774), or skips the inner signature of a nested JWT. | Validate every cryptographic layer; let the application require JWS, JWE, or nested explicitly (3.3). |
| Ciphertext length leaks (2.4) | Compression before encryption reveals plaintext content through size. | Do not use `zip` unless the threat model allows it (3.6). |
| Invalid-curve attacks (2.5) | An `epk` point that is not on the curve leaks the recipient's private key through ECDH-ES. | The library must validate points (NIST SP 800-56A partial validation for P-curves) (3.4). |
| Multiple JSON encodings (2.6) | UTF-16 or UTF-32 JSON is parsed differently by different components. | UTF-8 only (3.7). |
| Substitution (2.7) | A token meant for service A is replayed at service B. | Validate `iss`, `sub`, and `aud` (3.8, 3.9). |
| Cross-JWT confusion (2.8) | An ID token or other JWT kind is accepted as an access token. | Explicit typing and mutually exclusive validation rules (3.11, 3.12). |
| Indirect attacks (2.9) | `kid`, `jku`, `x5u`, or claim values drive SQL, LDAP, file, or HTTP lookups: injection or SSRF. | Treat header and claim values as attacker input; allowlist URLs; block loopback and private addresses when no allowlist exists (3.10). |
| PBES2 iteration DoS (2.10) | A huge `p2c` burns CPU on the recipient. | Cap `p2c`; the update recommends rejecting values above 1,200,000 (twice OWASP's 600,000) (3.13). |
| Decompression bomb (2.12) | A tiny `zip` JWE inflates to gigabytes. | Cap decompressed size; libraries commonly use a few hundred KB, for example 250 KB (3.15). |
| JWT format confusion (2.13) | A library verifies a JWS JSON Serialization, but the application reads claims by splitting the string as compact form. | Reject anything except base64url characters and dots before parsing; read claims only from the verifier's result (3.14). |

## Other Known Attacks

| Attack | Example | Mitigation |
|---|---|---|
| Embedded key trust | A library trusted the `jwk` header and verified the token with the attacker's key (CVE-2018-0114, Cisco node-jose). | Ignore `jwk`, `jku`, `x5u` unless a profile pins them. |
| "Psychic signatures" | Oracle Java SE 17.0.2 and 18 (versions listed by NVD) accepted ECDSA signatures with r = s = 0 for any message (CVE-2022-21449). | Keep crypto runtimes patched; test that all-zero signatures fail. |
| ECDSA nonce reuse or bias | Predictable per-signature nonces reveal the private key. | Libraries should use deterministic ECDSA (RFC 6979) or a strong RNG (JWT BCP update 3.2). |
| Padding oracles on RSA1_5 | Different errors for bad padding let attackers decrypt (Bleichenbacher). | Avoid `RSA1_5`; return one generic error; bind keys to one algorithm (RFC 7516 Sections 11.4-11.5). |
| Unbounded key sizes | Very large RSA keys or exponents make verification expensive. | Set upper limits on accepted key sizes (RFC 7518 Section 8.6). |
| Token-supplied JWKS discovery | Fetching keys from `iss` of an untrusted token turns any issuer into a trusted one. | Keep an explicit list of trusted issuers and their JWKS URLs. |

## Library Requirements

From the JWT BCP update, a JOSE or JWT library must (unless marked RECOMMENDED):

- Let callers restrict the permitted algorithms and never use algorithms outside that set.
- Check that `alg` and `enc` are consistent with the key found by `kid` (one key, one algorithm).
- Never produce or consume `none` unless the caller explicitly asks.
- Distinguish Unsecured JWTs, JWSs, JWEs, and nested JWTs so applications can require one kind.
- Validate ECDH inputs (MUST), and should cap PBES2 iterations and decompressed size (RECOMMENDED).
- Check the compact format before parsing.

When a library lacks one of these, add the check in application code and record why.

## Code Review Checklist

Use this when reviewing JWT code. Each "no" is a finding.

1. Does verification pass an explicit algorithm allowlist that does not include `none`?
2. Is each key bound to one algorithm and type (key objects or `Key(material, alg)`, not bare strings)?
3. Are keys loaded from configuration or the issuer's JWKS, never from `jku`, `x5u`, `jwk`, or an untrusted `iss`?
4. Are `iss` and `aud` checked against expected values, and is `exp` required?
5. Is `typ` checked for profiles that define it (`at+jwt`), and are ID tokens rejected by APIs?
6. Are claims read only from the verified result, never from a `decode()` without verification?
7. Are HMAC secrets random and at least the hash size, loaded from a secret store?
8. For JWE: are `alg` and `enc` allowlisted, is `zip` refused or capped, is `p2c` capped, is the inner signature verified?
9. Is `kid` used only as a map key, never in SQL, LDAP, file paths, or URLs?
10. Do error responses avoid echoing tokens, keys, or detailed crypto failure reasons?
11. Are there tests for `none`, algorithm confusion, wrong `aud`, wrong `iss`, expired, tampered payload, unknown `kid`, and wrong `typ`?

## Operational Rules

- Never log full tokens. Log the header and non-sensitive claims (`iss`, `sub`, `jti`, `exp`) at most.
- Never paste production tokens or keys into online debuggers or chat tools. Decode locally with `scripts/jose_inspect.py`.
- A leaked signing key or HMAC secret requires rotation and invalidation of every token it signed; a leaked token is valid until `exp`.
- Send bearer tokens only over TLS, in the `Authorization` header rather than URLs.
- Browser storage of tokens is an application security decision (XSS versus CSRF trade-offs); follow the OWASP guidance for your architecture: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html
- Use sender-constrained tokens (DPoP, RFC 9449, or mutual TLS) when token theft is a significant risk.

## Best Practices

- Allowlists, never blocklists, for algorithms, issuers, audiences, types, and key URLs.
- One key, one algorithm, one purpose.
- Validate every layer of a nested JWT.
- Require explicit typing for new token kinds.
- Write negative tests for every attack in the tables above.
