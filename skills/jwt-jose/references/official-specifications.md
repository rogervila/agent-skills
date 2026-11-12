---
name: "Official JOSE Specifications"
description: "Map of the IETF RFCs, IANA registries, active drafts, and vendor documentation that define JOSE and JWT, with publication status checked on 2026-11-12 and source-of-truth rules."
tags: [jose, jwt, rfc7515, rfc7516, rfc7517, rfc7518, rfc7519, rfc7520, rfc7638, rfc7797, rfc8037, rfc8725, rfc9068, rfc9864, rfc9964, iana, datatracker, source-of-truth]
---

# Official JOSE Specifications

Last checked: 2026-11-12. The IANA JOSE registry was last updated 2026-09-29.

Use the RFC text for normative behavior, the IANA registries for the current set of identifiers, and library documentation for API details. When an article, blog post, or this skill disagrees with an RFC, the RFC wins.

## Core Specifications

| Spec | Title | Read it for |
|---|---|---|
| [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515) | JSON Web Signature (JWS) | Header parameters (`alg`, `kid`, `jku`, `jwk`, `x5*`, `typ`, `cty`, `crit`), signing input, Compact and JSON serializations, validation steps (Section 5.2), security considerations (Section 10). |
| [RFC 7516](https://www.rfc-editor.org/rfc/rfc7516) | JSON Web Encryption (JWE) | Five-part structure, key management modes, AAD, encryption and decryption steps (Section 5), JSON serialization, distinguishing JWS from JWE (Section 9). |
| [RFC 7517](https://www.rfc-editor.org/rfc/rfc7517) | JSON Web Key (JWK) | JWK members (`kty`, `use`, `key_ops`, `alg`, `kid`, `x5*`), JWK Set (`keys`), encrypted JWKs. |
| [RFC 7518](https://www.rfc-editor.org/rfc/rfc7518) | JSON Web Algorithms (JWA) | Algorithm definitions and key size rules (Sections 3-5), key type parameters (Section 6), security considerations (Section 8), IANA registries. |
| [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519) | JSON Web Token (JWT) | Registered claims, NumericDate, nested JWTs, Unsecured JWTs, creating and validating a JWT (Section 7). |
| [RFC 7520](https://www.rfc-editor.org/rfc/rfc7520) | Examples of Protecting Content Using JOSE | Interoperability test vectors for every mode. |

## Extensions And Updates

| Spec | Title | Key points |
|---|---|---|
| [RFC 7638](https://www.rfc-editor.org/rfc/rfc7638) | JWK Thumbprint | Canonical hash of a key's required members; a good `kid`. |
| [RFC 9278](https://www.rfc-editor.org/rfc/rfc9278) | JWK Thumbprint URI | `urn:ietf:params:oauth:jwk-thumbprint:sha-256:<thumbprint>`. |
| [RFC 7797](https://www.rfc-editor.org/rfc/rfc7797) | JWS Unencoded Payload Option | `"b64": false`, which must be listed in `crit`; used with detached payloads. |
| [RFC 8037](https://www.rfc-editor.org/rfc/rfc8037) | CFRG Elliptic Curves in JOSE | `OKP` key type, Ed25519/Ed448 signatures, X25519/X448 key agreement. |
| [RFC 8812](https://www.rfc-editor.org/rfc/rfc8812) | COSE and JOSE Registrations for WebAuthn Algorithms | `ES256K` with `secp256k1`. |
| [RFC 9864](https://www.rfc-editor.org/rfc/rfc9864) | Fully-Specified Algorithms for JOSE and COSE (October 2025) | Registers `Ed25519` and `Ed448`; deprecates the polymorphic `EdDSA`. |
| [RFC 9964](https://www.rfc-editor.org/rfc/rfc9964) | ML-DSA for JOSE and COSE (May 2026) | Post-quantum `ML-DSA-44`, `ML-DSA-65`, `ML-DSA-87`; `AKP` key type with `pub` and `priv` (a 32-byte seed). |

## Security Guidance

| Document | Status on 2026-11-12 | Use |
|---|---|---|
| [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725) (BCP 225) | Published best current practice. | Threats and mitigations for JWT: algorithm verification, appropriate algorithms, validate all operations, issuer, audience, explicit typing. |
| [draft-ietf-oauth-rfc8725bis](https://datatracker.ietf.org/doc/draft-ietf-oauth-rfc8725bis/) (revision -10) | Approved; in the RFC Editor queue. Obsoletes RFC 8725 when published. | Adds: algorithm allowlists instead of blocklists, one key per algorithm, PBES2 `p2c` limit, JWE decompression limit, JWT format check, no `none` by default, case-sensitive `alg`, fully-specified algorithms. |
| [draft-ietf-jose-deprecate-none-rsa15](https://datatracker.ietf.org/doc/draft-ietf-jose-deprecate-none-rsa15/) (revision -08) | Approved; in the RFC Editor queue. IANA action in progress, so the registry still lists `none` as Optional and `RSA1_5` as Recommended-. | Deprecates `none` and `RSA1_5`. |
| [draft-ietf-jose-hpke-encrypt](https://datatracker.ietf.org/doc/draft-ietf-jose-hpke-encrypt/) (revision -22) | Approved; in the RFC Editor queue. IANA already lists its `HPKE-*` identifiers. | HPKE-based JWE algorithms. Check library support before use. |

Re-check these statuses before quoting them: drafts in the RFC Editor queue become RFCs with new numbers.

## Token Profiles Built On JWT

| Spec | Token | Explicit `typ` |
|---|---|---|
| [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068) | OAuth 2.0 access token in JWT format | `at+jwt` (resource servers must reject other values) |
| [RFC 8417](https://www.rfc-editor.org/rfc/rfc8417) | Security Event Token (SET) | `secevent+jwt` |
| [RFC 9449](https://www.rfc-editor.org/rfc/rfc9449) | DPoP proof | `dpop+jwt` |
| [OpenID Connect Back-Channel Logout 1.0](https://openid.net/specs/openid-connect-backchannel-1_0.html) | Logout token | `logout+jwt` |
| [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) | ID token | none mandated; validation rules in Section 3.1.3.7 |

## IANA Registries

| Registry | URL | Contains |
|---|---|---|
| JOSE registries | https://www.iana.org/assignments/jose/jose.xhtml | Header parameters, algorithms (with Required/Recommended/Optional/Deprecated status), compression, key types, curves, JWK parameters, `use`, `key_ops`, JWK Set parameters. |
| JWT claims | https://www.iana.org/assignments/jwt/jwt.xhtml | Registered and public claim names (`iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti`, `cnf`, OIDC claims, and more). |
| Media types | https://www.iana.org/assignments/media-types/media-types.xhtml | `application/jwt`, `application/jose`, `application/jose+json`, `application/jwk+json`, `application/jwk-set+json`, `application/at+jwt`, and other `+jwt` types. |

## Working Group And Tooling

| Resource | URL |
|---|---|
| IETF JOSE working group documents | https://datatracker.ietf.org/wg/jose/documents/ |
| IETF OAuth working group documents (JWT BCP, JWT profiles) | https://datatracker.ietf.org/wg/oauth/documents/ |
| Datatracker API for a document's state | `https://datatracker.ietf.org/api/v1/doc/document/<draft-name>/?format=json` |
| RFC plain text | `https://www.rfc-editor.org/rfc/rfc<NNNN>.txt` |

## Vendor Documentation Linked From The Source Article

| Topic | URL | Note |
|---|---|---|
| Auth0 JWT claims | https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-token-claims | Registered, public, and private claims; namespacing custom claims. |
| Auth0 JWE access tokens | https://auth0.com/docs/secure/tokens/access-tokens/json-web-encryption | Auth0 signs the access token (JWS) and then encrypts it (JWE Compact): a nested JWT. Its header example swaps `alg` and `enc`. |
| Auth0 JSON Web Key Sets | https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-key-sets | Tenant JWKS at `https://{yourDomain}/.well-known/jwks.json`; cache it, refetch on unknown `kid`, rate-limit refetches. |
| Auth0 validate JWTs | https://auth0.com/docs/secure/tokens/json-web-tokens/validate-json-web-tokens | Use library `verify()`, not `decode()`; restrict algorithms. |
| Auth0 docs index for agents | https://auth0.com/llms.txt | Every docs page is also available as Markdown by appending `.md`. |

## Source-Of-Truth Rules

1. Normative behavior comes from the RFC text. Quote the section number.
2. Algorithm and parameter names come from the IANA registry. Status labels there (Required, Recommended+, Deprecated) are authoritative.
3. Approved drafts guide current best practice; mark them as drafts with their revision and date.
4. Library behavior comes from the installed version's source or tests, not from memory. Record the version you checked.
5. Vendor docs describe the vendor's deployment; do not generalize vendor limits or defaults to all JOSE implementations.

## Best Practices

- Link the exact RFC section that supports a security claim.
- Check the IANA registry before calling an algorithm current, deprecated, or unknown.
- Re-check draft status in the datatracker before telling a user a draft is still a draft.
- Prefer RFC 7520 vectors over hand-made tokens when testing interoperability.
