---
name: "JSON Web Signature (JWS)"
description: "JWS structure, signing input, Compact and JSON serializations, every registered header parameter and its trust implications, validation steps, signature formats, unsecured and unencoded payloads (RFC 7515, RFC 7797)."
tags: [jws, rfc7515, rfc7797, signature, mac, compact-serialization, json-serialization, alg, kid, jku, jwk, x5c, x5u, typ, cty, crit, b64, detached-payload, ecdsa]
---

# JSON Web Signature (JWS)

A JWS protects the integrity of a payload with a digital signature or a MAC. It does not hide the payload. In the source article's metaphor it is a clear envelope with a tamper-proof seal.

## Structure

A JWS has three logical parts:

| Part | Content |
|---|---|
| JWS Protected Header | JSON object with header parameters, integrity protected. |
| JWS Payload | Any octet sequence. For a JWT, the UTF-8 JSON Claims Set. |
| JWS Signature | Signature or MAC over the signing input. |

The signing input is:

```text
ASCII(BASE64URL(UTF8(JWS Protected Header)) || '.' || BASE64URL(JWS Payload))
```

BASE64URL is base64 with the URL-safe alphabet (`-` and `_`) and no `=` padding. Line breaks and whitespace are not allowed.

## Compact Serialization

```text
BASE64URL(UTF8(JWS Protected Header)) . BASE64URL(JWS Payload) . BASE64URL(JWS Signature)
```

Three segments, two dots. Only the protected header exists in this form. JWTs always use this serialization.

Example from RFC 7515 Appendix A.3 (ES256), decoded:

```json
{"alg":"ES256"}
```

The payload is the RFC 7515 example claims set, and the signature is 64 bytes (R || S).

## JSON Serializations

The JSON forms add an unprotected header and allow several signatures. They are not used for JWTs.

General JWS JSON Serialization:

```json
{
  "payload": "eyJpc3MiOiJodHRwczovL2lzc3Vlci5leGFtcGxlLmNvbSJ9",
  "signatures": [
    {
      "protected": "eyJhbGciOiJFUzI1NiJ9",
      "header": {"kid": "es256-2026-11"},
      "signature": "<base64url signature 1>"
    },
    {
      "protected": "eyJhbGciOiJSUzI1NiJ9",
      "header": {"kid": "rs256-2026-11"},
      "signature": "<base64url signature 2>"
    }
  ]
}
```

Flattened JWS JSON Serialization (one signature):

```json
{
  "payload": "eyJpc3MiOiJodHRwczovL2lzc3Vlci5leGFtcGxlLmNvbSJ9",
  "protected": "eyJhbGciOiJFUzI1NiJ9",
  "header": {"kid": "es256-2026-11"},
  "signature": "<base64url signature>"
}
```

Rules:

- The `header` member is not integrity protected. Put `alg` and anything security-relevant in `protected`.
- The same parameter name must not appear in both `protected` and `header`.
- At least one signature must validate. Which signatures must validate is an application decision.

## Header Parameters

| Parameter | Meaning | Trust implications |
|---|---|---|
| `alg` | Signature or MAC algorithm. Required. Case-sensitive. | Check it against an exact allowlist bound to the key. Never let it choose the key type. |
| `kid` | Hint identifying the key. Case-sensitive string. | Untrusted input. Look it up in a map of keys from trusted configuration or the issuer's JWKS. Never use it in SQL, LDAP, file paths, or commands. |
| `jku` | URL of a JWK Set containing the key. Must use TLS. | Never fetch a token-supplied URL unless it exactly matches an allowlist. Otherwise an attacker hosts the key. |
| `jwk` | The public key itself, embedded in the header. | A signature that verifies with an embedded key proves only that the sender has the matching private key. Use it only when the key is pinned or bound by the protocol (for example DPoP, RFC 9449). |
| `x5u` | URL of an X.509 certificate chain. | Same risk as `jku` (SSRF, key injection). |
| `x5c` | X.509 chain, standard base64 DER (not base64url), signing certificate first. | Trust only after PKIX path validation to a configured trust anchor, plus name and usage checks. |
| `x5t`, `x5t#S256` | SHA-1 or SHA-256 certificate thumbprint. | A lookup hint, like `kid`. |
| `typ` | Media type of the complete JWS. `application/` prefix may be omitted. Case-insensitive. | Use for explicit typing (`at+jwt`). `JWT` alone is not explicit typing. |
| `cty` | Media type of the payload. `JWT` means a nested JWT. | Validate the inner object as a full JWS or JWE with its own allowlist and keys. |
| `crit` | Names of extension parameters the recipient must understand. | Reject if any listed name is not understood. Must not be empty, list names defined by RFC 7515 or RFC 7518 (extension names such as `b64` are allowed), list duplicates, or list absent names. Must be protected. |
| `b64` | `false` means the payload is not base64url-encoded in the signing input (RFC 7797). | Must be protected and listed in `crit`. Usually combined with a detached payload. JWTs must not use `"b64": false` (RFC 7797 Section 7). |

Header parameter names must be unique. A parser must reject duplicates or keep only the last one; rejecting is safer.

## Validation Steps

Summary of RFC 7515 Section 5.2. If any step fails, the JWS is invalid.

1. Split the representation. Compact: exactly two dots, three segments.
2. Base64url-decode the protected header with no whitespace or extra characters.
3. Parse it as UTF-8 JSON. Reject duplicate names.
4. Form the JOSE Header (protected plus unprotected for JSON serializations). Reject a name that appears in both.
5. Confirm every required and `crit` parameter is understood and supported.
6. Decode the payload (unless `b64` is `false`) and the signature.
7. Validate the signature over the signing input with the algorithm in `alg`, using a key the application selected for that algorithm.
8. For JSON serializations, repeat per signature; at least one must validate.
9. Reject the JWS if the algorithm is not acceptable to the application, even when the signature is valid.

## Signature Formats

| Algorithm family | Signature size | Pitfall |
|---|---|---|
| HS256, HS384, HS512 | 32, 48, 64 bytes | Key must be at least the hash size; random, not a password. |
| RS*, PS* | Modulus size (256 bytes for 2048-bit) | Key must be 2048 bits or more. |
| ES256, ES384, ES512 | 64, 96, 132 bytes, fixed-size `R || S` | Not ASN.1 DER. Convert when using a crypto API that emits DER. ES512 is P-521 with SHA-512 (there is no P-512 curve). |
| ES256K | 64 bytes | `secp256k1` curve (RFC 8812). |
| Ed25519, Ed448 (and deprecated `EdDSA`) | 64, 114 bytes | OKP keys with `crv` `Ed25519` or `Ed448`. |
| ML-DSA-44, -65, -87 | 2420, 3309, 4627 bytes | AKP keys (RFC 9964); large tokens. |

## Signatures Versus MACs

A digital signature (RS*, PS*, ES*, Ed25519, ML-DSA) is created with a private key and verified with a public key. Many parties can verify; only the key holder can sign.

A MAC (HS*) uses one shared secret for both operations. Every verifier can also mint tokens. A MAC proves only that one of the secret holders produced the token, and cannot prove origin to a third party (RFC 7515 Section 10.5). Use HS* only when the issuer and all verifiers are the same trust domain.

## Unsecured JWS

`"alg": "none"` with an empty signature segment has no integrity protection. RFC 7518 Section 3.6 forbids accepting it by default; applications must opt in per object, never globally. The JWT BCP update forbids libraries from producing or consuming it unless the caller explicitly asks, and its deprecation is approved.

## Unencoded And Detached Payloads

RFC 7797 lets the signing input use the raw payload:

```json
{"alg":"HS256","b64":false,"crit":["b64"]}
```

With a detached payload, the compact form leaves the payload segment empty (`header..signature`) and the payload travels separately. The verifier must get the exact payload bytes from the protocol.

## Hand Decoding For Debugging

Decoding is not verification. Use this only to read a header while debugging, and prefer `scripts/jose_inspect.py`, which also flags risks.

```python
# decode_header.py - debugging only; the result is untrusted
import base64
import json
import sys


def b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def unverified_header(token: str) -> dict:
    return json.loads(b64url_decode(token.split(".")[0]))


if __name__ == "__main__":
    print(unverified_header(sys.argv[1]))
```

## Best Practices

- Pin the accepted algorithms per issuer and per key; reject everything else.
- Select the verification key from trusted configuration or the issuer's JWKS, using `kid` only as a lookup hint.
- Ignore `jku`, `x5u`, and `jwk` unless a profile requires them and they are pinned or allowlisted.
- Keep security parameters in the protected header.
- Use the Compact Serialization for JWTs and read claims only from the verified result.
- Prefer asymmetric signatures when more than one service verifies tokens.
