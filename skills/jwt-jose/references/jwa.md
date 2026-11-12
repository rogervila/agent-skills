---
name: "JSON Web Algorithms (JWA)"
description: "Registered JOSE algorithm identifiers with IANA implementation requirements as of 2026-09-29, key size rules, deprecations, fully-specified and post-quantum algorithms, key types and curves, and how to choose algorithms (RFC 7518, RFC 8037, RFC 8812, RFC 9864, RFC 9964)."
tags: [jwa, rfc7518, algorithms, iana, hs256, rs256, ps256, es256, es256k, eddsa, ed25519, ml-dsa, rsa-oaep, ecdh-es, a256gcm, deprecated, fully-specified, post-quantum, key-size]
---

# JSON Web Algorithms (JWA)

JWA (RFC 7518) defines the cryptographic algorithms and identifiers that JWS and JWE use, and created the IANA registries that later RFCs extend. Identifiers are case-sensitive strings.

Status values below are the "JOSE Implementation Requirements" column of the IANA registry, updated 2026-09-29: Required, Recommended (with + meaning likely to become Required, - meaning likely to be downgraded), Optional, Deprecated, Prohibited.

## JWS Algorithms (`alg` for signatures and MACs)

| `alg` | Algorithm | IANA status | Key |
|---|---|---|---|
| `HS256` | HMAC SHA-256 | Required | `oct`, at least 32 random bytes |
| `HS384` | HMAC SHA-384 | Optional | `oct`, at least 48 bytes |
| `HS512` | HMAC SHA-512 | Optional | `oct`, at least 64 bytes |
| `RS256` | RSASSA-PKCS1-v1_5 SHA-256 | Recommended | `RSA`, 2048 bits or more |
| `RS384`, `RS512` | RSASSA-PKCS1-v1_5 SHA-384/512 | Optional | `RSA`, 2048 bits or more |
| `PS256`, `PS384`, `PS512` | RSASSA-PSS with MGF1 | Optional | `RSA`, 2048 bits or more |
| `ES256` | ECDSA P-256 SHA-256 | Recommended+ | `EC` `P-256` |
| `ES384` | ECDSA P-384 SHA-384 | Optional | `EC` `P-384` |
| `ES512` | ECDSA P-521 SHA-512 | Optional | `EC` `P-521` |
| `ES256K` | ECDSA secp256k1 SHA-256 (RFC 8812) | Optional | `EC` `secp256k1` |
| `Ed25519` | EdDSA with Ed25519 (RFC 9864) | Optional | `OKP` `Ed25519` |
| `Ed448` | EdDSA with Ed448 (RFC 9864) | Optional | `OKP` `Ed448` |
| `EdDSA` | Polymorphic EdDSA (RFC 8037) | Deprecated (RFC 9864) | `OKP` `Ed25519` or `Ed448` |
| `ML-DSA-44`, `ML-DSA-65`, `ML-DSA-87` | ML-DSA, FIPS 204 (RFC 9964) | Optional | `AKP` |
| `none` | No signature (Unsecured JWS) | Optional; deprecation approved | none |

## JWE Key Management Algorithms (`alg`)

| `alg` | Mode | IANA status |
|---|---|---|
| `RSA1_5` | Key encryption, RSAES-PKCS1-v1_5 | Recommended-; deprecation approved |
| `RSA-OAEP` | Key encryption, OAEP with SHA-1 and MGF1-SHA-1 | Recommended+ |
| `RSA-OAEP-256` | Key encryption, OAEP with SHA-256 | Optional |
| `RSA-OAEP-384`, `RSA-OAEP-512` | Key encryption, OAEP with SHA-384/512 (registered from WebCrypto) | Optional |
| `A128KW`, `A256KW` | AES Key Wrap | Recommended |
| `A192KW` | AES Key Wrap | Optional |
| `A128GCMKW`, `A192GCMKW`, `A256GCMKW` | AES-GCM key wrap | Optional |
| `dir` | Direct encryption with a shared key | Recommended |
| `ECDH-ES` | Direct key agreement | Recommended+ |
| `ECDH-ES+A128KW`, `ECDH-ES+A256KW` | Key agreement with key wrapping | Recommended |
| `ECDH-ES+A192KW` | Key agreement with key wrapping | Optional |
| `PBES2-HS256+A128KW`, `PBES2-HS384+A192KW`, `PBES2-HS512+A256KW` | Password-based key wrapping | Optional |
| `HPKE-0` to `HPKE-7`, `HPKE-*-KE` | HPKE (draft-ietf-jose-hpke-encrypt, RFC Editor queue) | Optional |

`RSA-OAEP` still uses SHA-1 inside OAEP; that is not a known weakness for OAEP, but new deployments commonly choose `RSA-OAEP-256`.

## JWE Content Encryption Algorithms (`enc`)

| `enc` | IANA status |
|---|---|
| `A128CBC-HS256` | Required |
| `A256CBC-HS512` | Required |
| `A192CBC-HS384` | Optional |
| `A128GCM`, `A256GCM` | Recommended |
| `A192GCM` | Optional |

Sizes of CEK, IV, and tag: see `references/jwe.md`.

## Key Size Rules

| Rule | Source |
|---|---|
| HMAC key at least the hash output size (32 bytes for HS256). | RFC 7518 Section 3.2 |
| RSA keys 2048 bits or larger for RS*, PS*, RSA1_5, RSA-OAEP*. | RFC 7518 Sections 3.3, 3.5, 4.2, 4.3 |
| ECDSA signature is a fixed-length `R || S` octet string (64 bytes for ES256). | RFC 7518 Section 3.4 |
| AES-GCM IV is 96 bits; tag is 128 bits. | RFC 7518 Sections 4.7, 5.3 |
| PBES2 salt input 8 bytes or more; iteration count at least 1000 recommended. | RFC 7518 Sections 4.8.1.1-4.8.1.2 |
| Set upper limits on accepted key sizes to avoid CPU exhaustion. | RFC 7518 Section 8.6 |
| ML-DSA private key (`priv`) is the 32-byte seed. | RFC 9964 Section 4 |

## Fully-Specified Algorithms

RFC 9864 calls an identifier fully specified when it fixes every cryptographic parameter (curve, hash, KDF). `EdDSA` is polymorphic: the key's curve decides Ed25519 or Ed448. RFC 9864 registers `Ed25519` and `Ed448` and deprecates `EdDSA`. The JWT BCP update says new deployments should prefer fully-specified identifiers unless backward compatibility needs the old ones.

Before switching an issuer from `EdDSA` to `Ed25519`, confirm every verifier's library accepts `Ed25519`.

For encryption, RFC 9864 treats `alg` values that derive parameters from `enc` (such as `ECDH-ES` key length) as fully specified. It notes the ECDH-ES identifiers are polymorphic in the curve, but deprecates no encryption algorithm.

## Key Types And Curves

| `kty` | Members | Use | IANA status |
|---|---|---|---|
| `RSA` | `n`, `e` (private: `d`, `p`, `q`, `dp`, `dq`, `qi`, `oth`) | RS*, PS*, RSA-OAEP*, RSA1_5 | Required |
| `EC` | `crv`, `x`, `y` (private: `d`) | ES*, ECDH-ES* | Recommended+ |
| `oct` | `k` (secret) | HS*, A*KW, A*GCMKW, `dir`, PBES2 | Required |
| `OKP` | `crv`, `x` (private: `d`) | Ed25519/Ed448 signatures, X25519/X448 ECDH-ES | Optional |
| `AKP` | `alg`, `pub` (private: `priv`) | ML-DSA | Optional |

| `crv` | Key type | Use |
|---|---|---|
| `P-256` | EC | ES256, ECDH-ES (Recommended+) |
| `P-384`, `P-521` | EC | ES384, ES512, ECDH-ES |
| `secp256k1` | EC | ES256K |
| `Ed25519`, `Ed448` | OKP | Signatures only |
| `X25519`, `X448` | OKP | ECDH-ES only |

Ed25519/Ed448 keys must not be used for ECDH-ES, and X25519/X448 keys must not be used for signatures (RFC 8037 Sections 3.1 and 3.2).

## Choosing Algorithms

| Need | Choose | Why |
|---|---|---|
| Tokens verified by many services or third parties | `ES256` (or `Ed25519` if all verifiers support it) | Small keys and signatures, asymmetric. |
| Maximum interoperability, OAuth JWT access tokens | `RS256` (RFC 9068 requires support), or `PS256` | Universally supported. |
| One service issues and verifies its own tokens | `HS256` with a 32-byte random key | Fast; but every verifier can mint. |
| Encrypt to a public key | `ECDH-ES+A256KW` or `RSA-OAEP-256` with `A256GCM` | Recommended modes. |
| Encrypt with a shared key | `A256KW` or `dir` with `A256GCM` | Simple, no public key needed. |
| Prepare for post-quantum signatures | `ML-DSA-44`/`-65`/`-87` where libraries support it | Registered by RFC 9964; tokens get large. |
| Avoid | `none`, `RSA1_5`, `EdDSA` for new deployments, HMAC with passwords, PBES2 without limits | Deprecated or easily misused. |

## Best Practices

- Configure an explicit allowlist of algorithms per issuer and per key; never derive it from the token.
- Use each key with exactly one algorithm (JWT BCP update, Section 3.1).
- Check the IANA registry status before recommending an algorithm.
- Design for agility: carry `kid`, publish new keys before signing with them, and keep old keys until tokens signed with them expire.
