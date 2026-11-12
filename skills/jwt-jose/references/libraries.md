---
name: "JOSE Libraries And Verified Code Examples"
description: "How to pick a JOSE/JWT library and use it safely, with executed examples for JavaScript (jose 6.2.17), Python (PyJWT 2.15.1, joserfc 1.8.0), and PHP (firebase/php-jwt 7.2.1, web-token/jwt-library 4.2.7), plus a map of libraries for other languages."
tags: [libraries, jose, panva, nodejs, javascript, typescript, python, pyjwt, joserfc, php, firebase-php-jwt, web-token, jwt-framework, java, nimbus, go, dotnet, verify, sign, encrypt, jwks-client]
---

# JOSE Libraries And Verified Code Examples

Every example below was extracted from this file and executed on 2026-11-12 with the versions in the title, including negative tests (wrong `aud`, wrong `iss`, wrong `typ`, expired, tampered, `alg: none`, algorithm confusion, unknown `kid`). Results are in `references/verified-behavior.md`. Re-check APIs when the installed version differs.

## Choosing A Library

A library is acceptable when it:

1. Requires or accepts an explicit algorithm allowlist and never accepts `none` by default.
2. Binds keys to algorithms (key objects, or key plus algorithm), so `RS256` keys cannot be used for `HS256`.
3. Validates `exp` and `nbf` and can require and check `iss`, `aud`, and `typ`.
4. Fetches and caches JWKS with refetch on unknown `kid` and a cooldown, or lets you do so cleanly.
5. Separates "verify a JWS" from "decrypt a JWE", and supports nested JWTs explicitly.
6. Is maintained, has a security policy, and has had recent releases.

Prefer framework middleware that wraps such a library (for example ASP.NET Core JWT bearer authentication or Spring Security's resource server) when the application already uses that framework.

## JavaScript And TypeScript: `jose`

`jose` (https://github.com/panva/jose) runs on Node.js, browsers, Deno, Bun, and Cloudflare Workers. It covers JWS, JWE, JWK, JWKS, and JWT. Install: `npm install jose`.

### Issue A Typed Access Token

```javascript
// file: issue-access-token.mjs
import { SignJWT, calculateJwkThumbprint, exportJWK, generateKeyPair } from "jose";

// Run once at key-rotation time; keep privateKey in a secret store, publish only the JWKS.
export async function createSigningKey() {
  const { publicKey, privateKey } = await generateKeyPair("ES256", { extractable: true });
  const publicJwk = await exportJWK(publicKey);
  const kid = await calculateJwkThumbprint(publicJwk); // RFC 7638
  const jwks = { keys: [{ ...publicJwk, kid, alg: "ES256", use: "sig" }] };
  return { privateKey, kid, jwks };
}

export async function issueAccessToken({ privateKey, kid, issuer, audience, subject, clientId, scope }) {
  return new SignJWT({ client_id: clientId, scope })
    .setProtectedHeader({ alg: "ES256", kid, typ: "at+jwt" })
    .setIssuer(issuer)
    .setSubject(subject)
    .setAudience(audience)
    .setIssuedAt()
    .setExpirationTime("10m")
    .setJti(crypto.randomUUID())
    .sign(privateKey);
}
```

`generateKeyPair` returns non-extractable keys unless `extractable: true` is set; that option is needed only to export the public JWK in this example.

### Verify An Access Token With A Remote JWKS

```javascript
// file: verify-access-token.mjs
import { createRemoteJWKSet, jwtVerify } from "jose";

export function createAccessTokenVerifier({ issuer, audience, jwksUri, algorithms = ["ES256"] }) {
  // Caches keys (default 10 minutes) and refetches on an unknown kid after a 30 second cooldown.
  const jwks = createRemoteJWKSet(new URL(jwksUri));

  return async function verifyAccessToken(token) {
    const { payload, protectedHeader } = await jwtVerify(token, jwks, {
      algorithms, // exact allowlist; "none" is never accepted
      issuer, // exact match; the claim becomes required
      audience, // must contain this value; the claim becomes required
      typ: "at+jwt", // RFC 9068 explicit typing; "application/at+jwt" also matches
      clockTolerance: 30, // seconds of leeway for exp and nbf
      requiredClaims: ["exp", "iat", "sub", "jti", "client_id"],
    });
    return { claims: payload, header: protectedHeader };
  };
}
```

Notes for `jose` 6.2.17:

- Without `requiredClaims: ["exp"]`, a token with no `exp` is accepted.
- `decodeJwt` and `decodeProtectedHeader` do not verify anything; use them only for logging or routing.
- `jwtVerify` rejects JWE input and JWS JSON serializations, and does not check a minimum HMAC secret length.
- Defaults for decryption: PBES2 is refused unless listed, `maxPBES2Count` is 10000, `maxDecompressedLength` is 250000 bytes.

### Nested JWT: Sign Then Encrypt

```javascript
// file: nested-token.mjs
import { CompactEncrypt, compactDecrypt } from "jose";

// Encrypt an already signed JWT (a compact JWS) to the recipient's RSA-OAEP-256 public key.
export async function encryptSignedToken(signedJwt, recipientPublicKey) {
  return new CompactEncrypt(new TextEncoder().encode(signedJwt))
    .setProtectedHeader({ alg: "RSA-OAEP-256", enc: "A256GCM", cty: "JWT" })
    .encrypt(recipientPublicKey);
}

// Decrypt, then hand the inner JWS to the normal verifier: decryption alone proves nothing about the issuer.
export async function openNestedToken(nestedJwt, recipientPrivateKey, verifyInnerToken) {
  const { plaintext, protectedHeader } = await compactDecrypt(nestedJwt, recipientPrivateKey, {
    keyManagementAlgorithms: ["RSA-OAEP-256"],
    contentEncryptionAlgorithms: ["A256GCM"],
  });
  if (protectedHeader.cty?.toUpperCase() !== "JWT") {
    throw new Error("expected a nested JWT");
  }
  return verifyInnerToken(new TextDecoder().decode(plaintext));
}
```

## Python: PyJWT And joserfc

PyJWT (https://github.com/jpadilla/pyjwt) handles JWS-based JWTs and JWKS fetching. It does not do JWE. Install: `pip install "pyjwt[crypto]"`.

joserfc (https://github.com/authlib/joserfc) implements JWS, JWE, JWK, and JWT. Install: `pip install joserfc`.

### Verify An Access Token With PyJWT

```python
# file: verify_access_token.py
from __future__ import annotations

from typing import Any

import jwt  # PyJWT


class AccessTokenVerifier:
    def __init__(self, issuer: str, audience: str, jwks_uri: str, algorithms: list[str] | None = None) -> None:
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms or ["ES256"]
        # Caches the JWKS and refetches when a token carries an unknown kid.
        self.jwks_client = jwt.PyJWKClient(jwks_uri, cache_keys=True, lifespan=600)

    def verify(self, token: str) -> dict[str, Any]:
        header = jwt.get_unverified_header(token)  # routing only; trusted after decode() succeeds
        if str(header.get("typ", "")).lower() not in ("at+jwt", "application/at+jwt"):
            raise jwt.InvalidTokenError("unexpected typ")
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=self.algorithms,
            issuer=self.issuer,
            audience=self.audience,
            leeway=30,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
        )
```

Notes for PyJWT 2.15.1:

- `algorithms` is mandatory in `decode()`; omitting it raises `DecodeError`.
- A token with `aud` fails when you pass no `audience`; a token without `exp` passes unless `require` lists it.
- PyJWT does not check `typ`; check it yourself as above.
- It refuses PEM public keys as HMAC secrets and warns when an HMAC key is shorter than the hash size.
- `options={"verify_signature": False}` returns unverified claims; never use it for authorization.

### Nested JWT With joserfc

```python
# file: nested_token.py
from __future__ import annotations

from typing import Any

from joserfc import jwe, jwt
from joserfc.jwk import ECKey, KeySet, RSAKey

ENCRYPTION = jwe.JWERegistry(algorithms=["RSA-OAEP-256", "A256GCM"])


def issue_nested_token(claims: dict[str, Any], signing_key: ECKey, recipient_key: RSAKey) -> str:
    header = {"alg": "ES256", "kid": signing_key.kid, "typ": "at+jwt"}
    signed = jwt.encode(header, claims, signing_key, algorithms=["ES256"])
    outer = {"alg": "RSA-OAEP-256", "enc": "A256GCM", "cty": "JWT"}
    return jwe.encrypt_compact(outer, signed, recipient_key, registry=ENCRYPTION)


def open_nested_token(token: str, recipient_key: RSAKey, issuer_keys: KeySet, issuer: str, audience: str) -> dict[str, Any]:
    outer = jwe.decrypt_compact(token, recipient_key, registry=ENCRYPTION)
    if str(outer.protected.get("cty", "")).upper() != "JWT" or outer.plaintext is None:
        raise ValueError("expected a nested JWT")
    inner = jwt.decode(outer.plaintext, issuer_keys, algorithms=["ES256"])
    if str(inner.header.get("typ", "")).lower() not in ("at+jwt", "application/at+jwt"):
        raise ValueError("unexpected typ")
    jwt.JWTClaimsRegistry(
        leeway=30,
        iss={"essential": True, "value": issuer},
        aud={"essential": True, "value": audience},
        sub={"essential": True},
        exp={"essential": True},
    ).validate(inner.claims)
    return inner.claims
```

Notes for joserfc 1.8.0:

- `jwt.decode` verifies a JWS by default and refuses a JWE unless you pass a `JWERegistry`, so decryption is never mistaken for verification.
- Claims are not validated by `decode`; call `JWTClaimsRegistry(...).validate(claims)`.
- `jwk.thumbprint(dict)` hashes every member you pass; use `key.thumbprint()` or pass only the required members.

## PHP: firebase/php-jwt And web-token

firebase/php-jwt (https://github.com/firebase/php-jwt, now published from googleapis/php-jwt) signs and verifies JWS-based JWTs. Install: `composer require firebase/php-jwt`.

web-token/jwt-library (https://github.com/web-token/jwt-framework) implements JWS, JWE, JWK, and checkers. Install: `composer require web-token/jwt-library` plus a PSR-20 clock such as `symfony/clock` for time checkers.

### Verify An Access Token With firebase/php-jwt

```php
<?php
// file: verify-access-token.php

declare(strict_types=1);

use Firebase\JWT\JWK;
use Firebase\JWT\JWT;

/**
 * @param array{keys: list<array<string, mixed>>} $jwks JWK Set fetched from the issuer's jwks_uri and cached by the app
 */
function verifyAccessToken(string $token, array $jwks, string $issuer, string $audience): stdClass
{
    JWT::$leeway = 30;
    $keys = JWK::parseKeySet($jwks); // every Key is bound to its JWK "alg"; keys without "alg" are rejected
    $headers = new stdClass();
    $claims = JWT::decode($token, $keys, $headers); // signature, alg-to-key match, exp, nbf, iat

    $typ = strtolower((string) ($headers->typ ?? ''));
    if ($typ !== 'at+jwt' && $typ !== 'application/at+jwt') {
        throw new UnexpectedValueException('Unexpected typ');
    }
    if (($claims->iss ?? null) !== $issuer) {
        throw new UnexpectedValueException('Unexpected issuer');
    }
    if (!in_array($audience, (array) ($claims->aud ?? []), true)) {
        throw new UnexpectedValueException('Unexpected audience');
    }
    foreach (['exp', 'sub', 'jti'] as $required) {
        if (!isset($claims->{$required})) {
            throw new UnexpectedValueException("Missing {$required}");
        }
    }

    return $claims;
}
```

Notes for firebase/php-jwt 7.2.1:

- `JWT::decode` does not check `iss`, `aud`, or `typ`, and accepts a token without `exp`; check them yourself as above.
- Version 7 rejects HMAC keys shorter than the hash size, RSA keys under 2048 bits, and EC keys smaller than the curve size ("Provided key is too short").
- A `Key` is bound to one algorithm, which blocks algorithm confusion ("Incorrect key for this algorithm").
- `CachedKeySet` adds JWKS fetching and caching through PSR-18, PSR-17, and PSR-6 implementations.

### Decrypt A Nested JWT With web-token

```php
<?php
// file: decrypt-nested-token.php

declare(strict_types=1);

use Jose\Component\Checker\AlgorithmChecker;
use Jose\Component\Checker\HeaderCheckerManager;
use Jose\Component\Core\AlgorithmManager;
use Jose\Component\Core\JWK;
use Jose\Component\Encryption\Algorithm\ContentEncryption\A256GCM;
use Jose\Component\Encryption\Algorithm\KeyEncryption\RSAOAEP256;
use Jose\Component\Encryption\JWEDecrypter;
use Jose\Component\Encryption\JWETokenSupport;
use Jose\Component\Encryption\Serializer\CompactSerializer;

/** Returns the inner compact JWS; verify it next with the normal access token verifier. */
function decryptNestedToken(string $token, JWK $recipientPrivateKey): string
{
    $algorithms = new AlgorithmManager([new RSAOAEP256(), new A256GCM()]); // the only accepted alg and enc
    $jwe = (new CompactSerializer())->unserialize($token);
    (new HeaderCheckerManager([new AlgorithmChecker(['RSA-OAEP-256'])], [new JWETokenSupport()]))
        ->check($jwe, 0, ['alg', 'enc', 'cty']);

    if (!(new JWEDecrypter($algorithms))->decryptUsingKey($jwe, $recipientPrivateKey, 0)) {
        throw new UnexpectedValueException('Cannot decrypt token');
    }
    if (strtoupper((string) $jwe->getSharedProtectedHeaderParameter('cty')) !== 'JWT') {
        throw new UnexpectedValueException('Expected a nested JWT');
    }

    return $jwe->getPayload() ?? throw new UnexpectedValueException('Empty payload');
}
```

## Other Languages

These were not executed for this skill. Check each project's documentation for the current API and confirm it meets the selection criteria above.

| Language | Library | Notes |
|---|---|---|
| Java | Nimbus JOSE + JWT (https://connect2id.com/products/nimbus-jose-jwt) | Full JOSE; use `DefaultJWTProcessor` with a `JWSVerificationKeySelector` pinned to the expected algorithm and a claims verifier. |
| Java | jjwt (https://github.com/jwtk/jjwt) | JWS and JWE; uses typed keys. |
| Go | go-jose (https://github.com/go-jose/go-jose) | Full JOSE; parse functions take an explicit list of allowed algorithms. |
| Go | golang-jwt/jwt (https://github.com/golang-jwt/jwt) | JWS-based JWTs; use parser options to restrict methods and require claims. |
| .NET | Microsoft.IdentityModel.JsonWebTokens (https://github.com/AzureAD/azure-activedirectory-identitymodel-extensions-for-dotnet) | `JsonWebTokenHandler` with `TokenValidationParameters` (`ValidAlgorithms`, `ValidIssuer`, `ValidAudience`, `ValidTypes`). |
| Ruby | ruby-jwt (https://github.com/jwt/ruby-jwt) | JWS-based JWTs; pass the algorithm explicitly. |
| Rust | jsonwebtoken (https://github.com/Keats/jsonwebtoken) | JWS-based JWTs; `Validation` sets algorithms, issuer, audience. |

Avoid libraries whose verify function picks the algorithm from the token, accepts a bare string as "the key" for every algorithm, or has no release in years.

## Best Practices

- Wrap the library call in one project function (like the examples) so every endpoint applies the same allowlists and claim rules.
- Pass expected `iss`, `aud`, `typ`, algorithms, and required claims explicitly, even when a library has defaults.
- Pin the library version and re-read its changelog for security fixes when upgrading.
- Keep negative tests next to the wrapper: `none`, algorithm confusion, wrong `aud`, wrong `iss`, wrong `typ`, expired, tampered, unknown `kid`.
