---
name: "JSON Web Encryption (JWE)"
description: "JWE five-part structure, key management modes, content encryption algorithms with IV and tag sizes, header parameters, encryption and decryption rules, JSON serializations, nested JWTs, and why decryption is not authentication (RFC 7516, RFC 7518)."
tags: [jwe, rfc7516, rfc7518, encryption, confidentiality, cek, aad, key-management, rsa-oaep, ecdh-es, aes-kw, dir, pbes2, a256gcm, cbc-hmac, nested-jwt, cty, zip, epk]
---

# JSON Web Encryption (JWE)

A JWE gives confidentiality and integrity to a payload using authenticated encryption. In the source article's metaphor it is a locked, opaque metal box. It does not, by itself, prove who created it.

## Structure

| Part | Content |
|---|---|
| JWE Protected Header | JSON header; also used as AAD, so it is integrity protected. |
| JWE Encrypted Key | The Content Encryption Key (CEK), encrypted or wrapped for the recipient. Empty for `dir` and `ECDH-ES`. |
| JWE Initialization Vector | Random IV for the content encryption. |
| JWE Ciphertext | Encrypted payload. |
| JWE Authentication Tag | Integrity tag over ciphertext and AAD. |

Compact Serialization (five segments, four dots):

```text
BASE64URL(UTF8(JWE Protected Header)) . BASE64URL(JWE Encrypted Key) . BASE64URL(JWE Initialization Vector) . BASE64URL(JWE Ciphertext) . BASE64URL(JWE Authentication Tag)
```

The Additional Authenticated Data is `ASCII(BASE64URL(UTF8(JWE Protected Header)))`, so changing any header byte breaks decryption.

## Two Algorithms Per JWE

| Header | Chooses | Examples |
|---|---|---|
| `alg` | How the CEK is delivered (key management). | `RSA-OAEP-256`, `ECDH-ES+A256KW`, `A256KW`, `dir` |
| `enc` | How the payload is encrypted with the CEK (content encryption). | `A256GCM`, `A128CBC-HS256` |

A JWE header always has both. If `enc` exists, the object is a JWE (RFC 7516 Section 9).

## Key Management Modes

| Mode | `alg` values | Encrypted Key segment | Key the recipient needs |
|---|---|---|---|
| Key Encryption | `RSA-OAEP`, `RSA-OAEP-256` (`RSA-OAEP-384`/`-512` registered from WebCrypto); `RSA1_5` deprecated | CEK encrypted to the recipient's public key (256 bytes for RSA-2048) | RSA private key |
| Key Wrapping | `A128KW`, `A192KW`, `A256KW`; `A128GCMKW`, `A192GCMKW`, `A256GCMKW`; `PBES2-HS256+A128KW` and friends | CEK wrapped with a symmetric key (AES-KW adds 8 bytes) | Shared symmetric key or password |
| Direct Key Agreement | `ECDH-ES` | Empty; the CEK is derived with ECDH and Concat KDF | EC or X25519/X448 private key |
| Key Agreement with Key Wrapping | `ECDH-ES+A128KW`, `ECDH-ES+A192KW`, `ECDH-ES+A256KW` | CEK wrapped with the agreed key | EC or X25519/X448 private key |
| Direct Encryption | `dir` | Empty; the shared key is the CEK | Shared symmetric key of the `enc` size |

HPKE-based algorithms (`HPKE-0` to `HPKE-7`, `-KE` variants) are in the IANA registry from draft-ietf-jose-hpke-encrypt, approved and in the RFC Editor queue on 2026-11-12. Confirm library support before using them.

## Content Encryption Algorithms

| `enc` | CEK size | IV | Tag | Status |
|---|---|---|---|---|
| `A128GCM` | 16 bytes | 12 bytes (96 bits) | 16 bytes | Recommended |
| `A192GCM` | 24 bytes | 12 bytes | 16 bytes | Optional |
| `A256GCM` | 32 bytes | 12 bytes | 16 bytes | Recommended |
| `A128CBC-HS256` | 32 bytes (MAC key plus AES key) | 16 bytes | 16 bytes | Required |
| `A192CBC-HS384` | 48 bytes | 16 bytes | 24 bytes | Optional |
| `A256CBC-HS512` | 64 bytes | 16 bytes | 32 bytes | Required |

AES-GCM rules (RFC 7518 Section 8.4): never reuse an IV with the same key, and use one key for at most 2^32 encryptions. Libraries generate a fresh random CEK and IV per JWE in the key encryption, key wrapping, and key agreement modes. With `dir`, the same key is reused for every message, so the 2^32 limit applies to that key.

## Header Parameters

JWE uses the JWS header parameters (`kid`, `jku`, `jwk`, `x5u`, `x5c`, `x5t`, `x5t#S256`, `typ`, `cty`, `crit`) with the same trust rules, plus:

| Parameter | Meaning | Notes |
|---|---|---|
| `alg` | Key management algorithm. | Allowlist per recipient key. |
| `enc` | Content encryption algorithm. | Allowlist separately. |
| `zip` | Compression before encryption (`DEF`). | Avoid: leaks plaintext through length and enables decompression bombs. If accepted, cap the decompressed size. |
| `epk` | Sender's ephemeral public key for ECDH-ES. | The library must check the point is on the recipient's curve (invalid-curve attack). |
| `apu`, `apv` | Agreement PartyUInfo and PartyVInfo for the KDF. | Optional context binding. |
| `iv`, `tag` | IV and tag for AES-GCM key wrapping. | Required for `A*GCMKW`. |
| `p2s`, `p2c` | PBES2 salt input (8 bytes or more) and iteration count. | Cap `p2c` on receipt; a huge value is a CPU denial of service. |
| `iss`, `sub`, `aud` | Claims replicated in the header (RFC 7519 Section 5.3). | Readable without decryption. Check they equal the decrypted claims before use. |

## Encryption Steps

Summary of RFC 7516 Section 5.1:

1. Pick the key management mode from `alg`.
2. Generate a random CEK of the size `enc` needs (except `dir`, ECDH-ES).
3. Deliver the CEK: encrypt, wrap, or derive it. For `dir` and `ECDH-ES` the encrypted key is empty.
4. Generate a random IV of the size `enc` needs.
5. Optionally compress (not recommended).
6. Encrypt the plaintext with the CEK, IV, and AAD; get ciphertext and tag.
7. Serialize the five parts.

## Decryption Rules

1. Parse five segments (or the JSON form) and reject duplicate header names.
2. Check `alg` and `enc` against the allowlists for this recipient key; check `crit`.
3. Recover the CEK; for ECDH-ES validate `epk` first; for PBES2 enforce a `p2c` cap.
4. Decrypt and verify the tag over ciphertext and AAD.
5. Decompress only if `zip` is present and allowed, with a size cap.
6. Report every failure in steps 3 to 5 as one generic error. Distinct errors for key format, padding, or length create an oracle (RFC 7516 Sections 11.4 and 11.5). On a malformed encrypted key, continue with a random CEK so timing does not leak.

## JSON Serializations

General JWE JSON Serialization (several recipients share one ciphertext):

```json
{
  "protected": "eyJlbmMiOiJBMjU2R0NNIn0",
  "unprotected": {"jku": "https://issuer.example.com/jwks.json"},
  "recipients": [
    {"header": {"alg": "RSA-OAEP-256", "kid": "rsa-2026-11"}, "encrypted_key": "<base64url>"},
    {"header": {"alg": "ECDH-ES+A256KW", "kid": "ec-2026-11", "epk": {"kty": "EC", "crv": "P-256", "x": "<base64url>", "y": "<base64url>"}}, "encrypted_key": "<base64url>"}
  ],
  "aad": "<optional base64url additional authenticated data>",
  "iv": "<base64url>",
  "ciphertext": "<base64url>",
  "tag": "<base64url>"
}
```

The Flattened form puts `header` and `encrypted_key` at the top level for a single recipient. JWTs do not use either JSON form.

## Nested JWTs

To get both authenticity and confidentiality, sign first, then encrypt (RFC 7519 Section 11.2):

1. Create a JWS whose payload is the JWT Claims Set, with the explicit `typ` (for example `at+jwt`) on this inner JWS.
2. Encrypt the compact JWS as the JWE plaintext, with `"cty": "JWT"` in the JWE header.
3. The recipient decrypts, sees `cty` `JWT`, then fully validates the inner JWS: algorithm allowlist, issuer key, claims.

Auth0's JWE access tokens follow this pattern: a signed JWT access token encrypted to the API's public key.

## Decryption Is Not Authentication

Anyone who knows the recipient's public key can create a valid JWE for it. Successful decryption proves the content was not modified after encryption, not who wrote it. Libraries that treat "decrypted" as "verified" allowed forged tokens (CVE-2023-51774, cited by the JWT BCP update). For authentication:

- Require a signed JWT (JWS) or a nested JWT.
- Make the API that verifies a token refuse a JWE, and the API that decrypts refuse to skip the inner signature check.
- With `dir` or symmetric key wrapping, every holder of the shared key can create tokens; treat it like HS256.

## Choosing Algorithms

| Situation | `alg` | `enc` |
|---|---|---|
| Encrypt to a recipient's public key, broad support | `RSA-OAEP-256` (2048-bit key or larger) | `A256GCM` |
| Encrypt to a recipient's EC or X25519 key | `ECDH-ES+A256KW` or `ECDH-ES` | `A256GCM` |
| Both sides share a symmetric key | `A256KW` (or `dir` with a 32-byte key) | `A256GCM` |
| Need to interoperate with peers that only support CBC-HMAC | any of the above | `A128CBC-HS256` or `A256CBC-HS512` |
| Avoid | `RSA1_5`, `PBES2` without a `p2c` cap, `zip` | |

## Best Practices

- Allowlist `alg` and `enc` separately for each decryption key.
- Use a fresh CEK and IV per message; never reuse an AES-GCM IV with the same key.
- Do not compress; if you must accept `zip`, cap the decompressed size (the JWT BCP update cites limits around 250 KB).
- Cap PBES2 `p2c` (the JWT BCP update recommends rejecting more than 1,200,000).
- Return one generic decryption error.
- For authentication, sign then encrypt, and always verify the inner signature.
