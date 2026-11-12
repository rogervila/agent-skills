#!/usr/bin/env python3
"""Read-only inspector for JOSE objects (JWS, JWE, JWT) and JSON Web Keys.

It decodes and lints. It NEVER verifies a signature against your keys and NEVER
decrypts anything, so every header and claim it prints is untrusted data.
The only cryptographic check it runs is an HMAC test against a short list of
publicly documented demo secrets (for example the jwt.io default), to flag
tokens that anyone can forge.

Usage:
    python jose_inspect.py token TOKEN [--now EPOCH_SECONDS]
    python jose_inspect.py token - [--now EPOCH_SECONDS]      (read token from stdin)
    python jose_inspect.py jwk FILE                           (a JWK or a JWK Set)
    python jose_inspect.py jwk -                              (read JSON from stdin)

Output: one JSON document on stdout with the decoded structure and a list of
findings ({"level": "error" | "warning" | "info", "code": ..., "message": ...}).
Private key members (d, p, q, dp, dq, qi, oth, k, priv) and signatures are never
printed.

Exit codes:
    0  parsed, no warning or error findings
    1  parsed, at least one warning or error finding
    2  input is not a parseable JOSE object, JWK, or JWK Set (or bad arguments)

Standard library only; Python 3.8+.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import math
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

Finding = Dict[str, str]

COMPACT_CHARS = re.compile(r"^[A-Za-z0-9_.-]*$")
SEGMENT_CHARS = re.compile(r"^[A-Za-z0-9_-]*$")

JWS_ALGS = {
    "HS256", "HS384", "HS512",
    "RS256", "RS384", "RS512",
    "PS256", "PS384", "PS512",
    "ES256", "ES384", "ES512", "ES256K",
    "EdDSA", "Ed25519", "Ed448",
    "ML-DSA-44", "ML-DSA-65", "ML-DSA-87",
    "none",
}
JWE_ALGS = {
    "RSA1_5", "RSA-OAEP", "RSA-OAEP-256", "RSA-OAEP-384", "RSA-OAEP-512",
    "A128KW", "A192KW", "A256KW",
    "dir",
    "ECDH-ES", "ECDH-ES+A128KW", "ECDH-ES+A192KW", "ECDH-ES+A256KW",
    "A128GCMKW", "A192GCMKW", "A256GCMKW",
    "PBES2-HS256+A128KW", "PBES2-HS384+A192KW", "PBES2-HS512+A256KW",
}
# HPKE algorithms are registered by draft-ietf-jose-hpke-encrypt (RFC Editor queue, 2026-11).
HPKE_ALGS = {"HPKE-0", "HPKE-1", "HPKE-2", "HPKE-3", "HPKE-4", "HPKE-5", "HPKE-6", "HPKE-7",
             "HPKE-0-KE", "HPKE-1-KE", "HPKE-2-KE", "HPKE-3-KE", "HPKE-5-KE", "HPKE-7-KE"}

# enc -> (CEK bytes, IV bytes, tag bytes)
ENC_PARAMS = {
    "A128GCM": (16, 12, 16),
    "A192GCM": (24, 12, 16),
    "A256GCM": (32, 12, 16),
    "A128CBC-HS256": (32, 16, 16),
    "A192CBC-HS384": (48, 16, 24),
    "A256CBC-HS512": (64, 16, 32),
}
HMAC_SIZES = {"HS256": 32, "HS384": 48, "HS512": 64}
HMAC_HASHES = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}
FIXED_SIGNATURE_SIZES = {
    "ES256": 64, "ES256K": 64, "ES384": 96, "ES512": 132,
    "Ed25519": 64, "Ed448": 114,
    "ML-DSA-44": 2420, "ML-DSA-65": 3309, "ML-DSA-87": 4627,
}
RSA_SIG_ALGS = {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512"}
RSA_ENC_ALGS = {"RSA1_5", "RSA-OAEP", "RSA-OAEP-256", "RSA-OAEP-384", "RSA-OAEP-512"}
KEY_WRAP_ALGS = {"A128KW", "A192KW", "A256KW", "ECDH-ES+A128KW", "ECDH-ES+A192KW", "ECDH-ES+A256KW",
                 "PBES2-HS256+A128KW", "PBES2-HS384+A192KW", "PBES2-HS512+A256KW"}
GCM_KW_ALGS = {"A128GCMKW", "A192GCMKW", "A256GCMKW"}
EMPTY_KEY_ALGS = {"dir", "ECDH-ES"}

# Publicly documented demo secrets. A token that verifies with one of them is forgeable by anyone.
DEMO_SECRETS = (b"your-256-bit-secret", b"your-384-bit-secret", b"your-512-bit-secret", b"secret")

KNOWN_TYPES = {
    "application/jwt": "generic JWT (RFC 7519); not explicit typing",
    "application/at+jwt": "OAuth 2.0 JWT access token (RFC 9068)",
    "application/secevent+jwt": "Security Event Token (RFC 8417)",
    "application/dpop+jwt": "DPoP proof (RFC 9449)",
    "application/logout+jwt": "OpenID Connect Back-Channel Logout token",
}
SENSITIVE_CLAIM = re.compile(r"(passw|pwd|secret|ssn|social.?security|credit.?card|card.?number|cvv|api.?key|private.?key)", re.I)
SUSPICIOUS_KID = re.compile(r"(\.\.|/|\\|['\";`]|\s|\x00|\$\{)")

REGISTERED_HEADER_NAMES = {"alg", "jku", "jwk", "kid", "x5u", "x5c", "x5t", "x5t#S256", "typ", "cty", "crit",
                           "enc", "zip", "epk", "apu", "apv", "iv", "tag", "p2s", "p2c"}

PRIVATE_MEMBERS = {
    "RSA": ("d", "p", "q", "dp", "dq", "qi", "oth"),
    "EC": ("d",),
    "OKP": ("d",),
    "oct": ("k",),
    "AKP": ("priv",),
}
REQUIRED_MEMBERS = {
    "RSA": ("e", "kty", "n"),
    "EC": ("crv", "kty", "x", "y"),
    "OKP": ("crv", "kty", "x"),
    "oct": ("k", "kty"),
    "AKP": ("alg", "kty", "pub"),
}
EC_COORDINATE_BYTES = {"P-256": 32, "P-384": 48, "P-521": 66, "secp256k1": 32}
OKP_KEY_BYTES = {"Ed25519": 32, "Ed448": 57, "X25519": 32, "X448": 56}
ALG_EC_CURVE = {"ES256": "P-256", "ES384": "P-384", "ES512": "P-521", "ES256K": "secp256k1"}
# Exact symmetric key sizes; "enc" names appear as a JWK "alg" for keys used with "dir".
OCT_EXACT_BYTES = {"A128KW": 16, "A192KW": 24, "A256KW": 32, "A128GCMKW": 16, "A192GCMKW": 24, "A256GCMKW": 32,
                   **{enc: params[0] for enc, params in ENC_PARAMS.items()}}
SIGNING_ALGS = JWS_ALGS - {"none"}


class InputError(Exception):
    """The input cannot be parsed as the requested JOSE structure."""


class DuplicateKeyError(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


def _no_duplicates(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not valid JSON (RFC 8259)")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"number {text[:20]} is out of range")
    return value


def strict_json(text: str) -> Any:
    """Parse RFC 8259 JSON: no duplicate names, no NaN or Infinity, bounded nesting."""
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant,
                          parse_float=_finite_float)
    except RecursionError as error:
        raise ValueError("JSON nesting is too deep") from error


def text_value(value: Any) -> Optional[str]:
    """Return value when it is a string, else None (keeps dict lookups safe from unhashable JSON values)."""
    return value if isinstance(value, str) else None


def numeric(value: Any) -> Optional[float]:
    """Return a finite float for a JSON number, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def b64url_decode(segment: str) -> bytes:
    if not SEGMENT_CHARS.match(segment):
        raise InputError("segment contains characters outside the base64url alphabet")
    if len(segment) % 4 == 1:
        raise InputError("segment has an impossible base64url length")
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError) as error:
        raise InputError(f"invalid base64url: {error}") from error


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def add(findings: List[Finding], level: str, code: str, message: str) -> None:
    findings.append({"level": level, "code": code, "message": message})


def normalize_media_type(value: str) -> str:
    lowered = value.strip().lower()
    return lowered if "/" in lowered else f"application/{lowered}"


def decode_json_segment(segment: str, label: str) -> Any:
    raw = b64url_decode(segment)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InputError(f"{label} is not UTF-8") from error
    try:
        return strict_json(text)
    except DuplicateKeyError as error:
        raise InputError(f"{label} contains the duplicate member name {error.name!r}") from error
    except ValueError as error:
        raise InputError(f"{label} is not valid JSON: {error}") from error


# --------------------------------------------------------------------------- tokens


def check_common_header(header: Dict[str, Any], findings: List[Finding]) -> None:
    for name in ("jku", "x5u"):
        if name in header:
            add(findings, "warning", "REMOTE_KEY_URL",
                f'"{name}" points to a remote key source ({header[name]!r}). Never fetch keys from a token-supplied URL '
                "unless it matches an exact allowlist; otherwise it enables key injection and SSRF.")
    if "jwk" in header:
        add(findings, "warning", "EMBEDDED_JWK",
            'The header embeds its own "jwk". A signature that verifies with an attacker-supplied key proves nothing; '
            "only use keys from trusted configuration or the issuer's JWKS.")
    if "x5c" in header:
        add(findings, "info", "X5C_PRESENT",
            '"x5c" carries a certificate chain. Accept it only after PKIX path validation to a configured trust anchor.')
    kid = header.get("kid")
    if kid is not None:
        if not isinstance(kid, str):
            add(findings, "error", "KID_NOT_STRING", '"kid" must be a string.')
        elif SUSPICIOUS_KID.search(kid):
            add(findings, "warning", "SUSPICIOUS_KID",
                f'"kid" {kid!r} contains path, quote, or whitespace characters. Treat it as untrusted input: look it up in '
                "a map of known keys, never in SQL, LDAP, or file paths.")
    typ = header.get("typ")
    if typ is None:
        add(findings, "info", "TYP_MISSING",
            'No "typ" header. New kinds of JWTs should use explicit typing (for example "at+jwt") to prevent cross-JWT confusion.')
    elif not isinstance(typ, str):
        add(findings, "error", "TYP_NOT_STRING", '"typ" must be a string.')
    else:
        media = normalize_media_type(typ)
        if media == "application/jwt":
            add(findings, "info", "TYP_JWT_NOT_EXPLICIT",
                '"typ": "JWT" only says this is a JWT; it does not distinguish token kinds (not explicit typing).')
        elif media in KNOWN_TYPES:
            add(findings, "info", "TYP_PROFILE", f'"typ" {typ!r} identifies: {KNOWN_TYPES[media]}.')
    cty = header.get("cty")
    if isinstance(cty, str) and normalize_media_type(cty) == "application/jwt":
        add(findings, "info", "NESTED_JWT",
            'cty "JWT": the payload is itself a JWT (nested JWT). Validate the inner token with its own algorithm allowlist and keys.')
    crit = header.get("crit")
    if crit is not None:
        if not isinstance(crit, list) or not crit or not all(isinstance(item, str) for item in crit):
            add(findings, "error", "CRIT_INVALID", '"crit" must be a non-empty array of strings.')
        else:
            problems = [item for item in crit if item not in header or item in REGISTERED_HEADER_NAMES]
            if problems or len(set(crit)) != len(crit):
                add(findings, "error", "CRIT_INVALID",
                    f'"crit" lists names that are duplicated, absent from the header, or defined by RFC 7515/7516/7518: {problems}.')
            add(findings, "info", "CRIT_PRESENT",
                f"The recipient must understand and process these extensions or reject the object: {crit}.")


def check_alg_spelling(alg: str, findings: List[Finding]) -> bool:
    known = JWS_ALGS | JWE_ALGS | HPKE_ALGS
    if alg in known:
        return True
    lowered = {name.lower(): name for name in known}
    if alg.lower() in lowered:
        add(findings, "error", "ALG_CASE_VARIANT",
            f'"alg" {alg!r} is a case variant of {lowered[alg.lower()]!r}. Algorithm names are case-sensitive; this '
            "pattern is used to bypass blocklists. Use an exact-match allowlist.")
    else:
        add(findings, "warning", "UNKNOWN_ALG", f'"alg" {alg!r} is not in the IANA JOSE registry known to this tool.')
    return False


def check_claims(claims: Dict[str, Any], now: int, findings: List[Finding], encrypted: bool) -> None:
    dates: Dict[str, Optional[float]] = {}
    for name in ("exp", "nbf", "iat"):
        if name in claims:
            value = numeric(claims[name])
            dates[name] = value
            if value is None:
                add(findings, "error", "CLAIM_TYPE",
                    f'"{name}" must be a NumericDate (finite JSON number of seconds since the epoch).')
            elif value > 100_000_000_000:
                add(findings, "warning", "TIMESTAMP_MILLISECONDS",
                    f'"{name}" = {claims[name]} looks like milliseconds. NumericDate values are seconds since the epoch.')
    exp, nbf, iat = dates.get("exp"), dates.get("nbf"), dates.get("iat")
    if "exp" not in claims:
        add(findings, "warning", "EXP_MISSING", 'No "exp" claim: the token never expires unless the recipient enforces a maximum age.')
    elif exp is not None and exp <= now:
        add(findings, "warning", "EXPIRED", f'"exp" is {int(now - exp)} seconds in the past (now={now}).')
    if nbf is not None and nbf > now:
        add(findings, "warning", "NOT_YET_VALID", f'"nbf" is {int(nbf - now)} seconds in the future (now={now}).')
    if iat is not None and iat > now + 300:
        add(findings, "warning", "IAT_IN_FUTURE", f'"iat" is {int(iat - now)} seconds in the future (now={now}).')
    if exp is not None and iat is not None and exp - iat > 86_400:
        add(findings, "info", "LONG_LIFETIME",
            f"Lifetime exp - iat = {round((exp - iat) / 3600, 1)} hours. Long-lived bearer tokens widen the replay window.")
    for name in ("iss", "sub"):
        if name in claims and not isinstance(claims[name], str):
            add(findings, "error", "CLAIM_TYPE", f'"{name}" must be a string (StringOrURI).')
    if "iss" not in claims:
        add(findings, "warning", "ISS_MISSING", 'No "iss" claim: the recipient cannot bind the token to a trusted issuer.')
    aud = claims.get("aud")
    if aud is None:
        add(findings, "warning", "AUD_MISSING", 'No "aud" claim: the token can be replayed at any recipient that trusts the issuer.')
    elif not (isinstance(aud, str) or (isinstance(aud, list) and all(isinstance(item, str) for item in aud))):
        add(findings, "error", "CLAIM_TYPE", '"aud" must be a string or an array of strings.')
    if not encrypted:
        sensitive = sorted(name for name in claims if SENSITIVE_CLAIM.search(name))
        if sensitive:
            add(findings, "warning", "SENSITIVE_DATA_IN_JWS",
                f"Claims {sensitive} look sensitive. A JWS payload is only base64url-encoded, not encrypted; anyone holding "
                "the token can read it. Remove the data or use JWE.")


def inspect_jws(segments: List[str], now: int, findings: List[Finding]) -> Dict[str, Any]:
    header = decode_json_segment(segments[0], "JOSE header")
    if not isinstance(header, dict):
        raise InputError("JOSE header is not a JSON object")
    result: Dict[str, Any] = {"kind": "JWS", "serialization": "compact", "verified": False, "header": header}
    alg = header.get("alg")
    if not isinstance(alg, str):
        add(findings, "error", "MISSING_ALG", 'The JOSE header has no string "alg" member.')
        alg = ""
    elif check_alg_spelling(alg, findings):
        if alg in JWE_ALGS or alg in HPKE_ALGS:
            add(findings, "error", "ALG_KIND_MISMATCH", f'"alg" {alg!r} is a JWE key management algorithm, but the object has 3 segments (JWS).')
        if "enc" in header:
            add(findings, "error", "ALG_KIND_MISMATCH", 'A JWS header must not contain "enc"; "enc" marks a JWE.')
        if alg == "none":
            add(findings, "warning", "ALG_NONE",
                'Unsecured JWS ("alg": "none"): no integrity protection. Reject it unless the application explicitly '
                "accepts unsecured objects for this specific context.")
        elif alg in HMAC_SIZES:
            add(findings, "info", "SYMMETRIC_ALG",
                f"{alg} is a MAC: every party that can verify can also mint tokens. Use it only when issuer and verifier "
                "are the same trust domain, with a random key of at least the hash size.")
        elif alg == "EdDSA":
            add(findings, "info", "POLYMORPHIC_ALG", '"EdDSA" is deprecated by RFC 9864; prefer the fully-specified "Ed25519" or "Ed448".')
    check_common_header(header, findings)

    b64 = header.get("b64", True)
    if b64 is False:
        crit = header.get("crit")
        if not (isinstance(crit, list) and "b64" in crit):
            add(findings, "error", "B64_WITHOUT_CRIT", '"b64": false requires "b64" in "crit" (RFC 7797 Section 6).')
        add(findings, "info", "UNENCODED_PAYLOAD",
            'RFC 7797 unencoded payload; the payload segment is not base64url-decoded. JWTs must not use "b64": false '
            "(RFC 7797 Section 7), so this is not a JWT.")
        result["payload_text"] = segments[1][:200]
    else:
        payload = b64url_decode(segments[1])
        cty = header.get("cty")
        if isinstance(cty, str) and normalize_media_type(cty) == "application/jwt":
            result["payload_text"] = payload.decode("utf-8", "replace")[:200]
        else:
            claims_error = False
            try:
                claims = strict_json(payload.decode("utf-8"))
            except DuplicateKeyError as error:
                add(findings, "error", "DUPLICATE_CLAIM", f"The claims set contains the duplicate member name {error.name!r}; reject it.")
                claims, claims_error = None, True
            except (UnicodeDecodeError, ValueError) as error:
                claims = None
                if payload.lstrip().startswith(b"{"):
                    claims_error = True
                    add(findings, "error", "INVALID_CLAIMS_JSON",
                        f"The payload looks like a claims set but is not valid UTF-8 RFC 8259 JSON ({error}); reject it.")
            if isinstance(claims, dict):
                result["claims"] = claims
                check_claims(claims, now, findings, encrypted=False)
            else:
                if not claims_error:
                    add(findings, "info", "PAYLOAD_NOT_JSON", "The payload is not a JSON object, so it is not a JWT Claims Set.")
                result["payload_text"] = payload.decode("utf-8", "replace")[:200]

    signature = b64url_decode(segments[2])
    result["signature_bytes"] = len(signature)
    if alg == "none" and signature:
        add(findings, "error", "NONE_WITH_SIGNATURE", 'An Unsecured JWS must have an empty signature segment.')
    if alg and alg != "none" and not signature:
        add(findings, "error", "EMPTY_SIGNATURE", f'"alg" is {alg!r} but the signature segment is empty.')
    if signature and alg in HMAC_SIZES and len(signature) != HMAC_SIZES[alg]:
        add(findings, "error", "SIGNATURE_LENGTH", f"{alg} MACs are {HMAC_SIZES[alg]} bytes; this one is {len(signature)}.")
    if signature and alg in FIXED_SIGNATURE_SIZES and len(signature) != FIXED_SIGNATURE_SIZES[alg]:
        hint = " ECDSA in JOSE uses the fixed-size R || S form, not DER." if alg.startswith("ES") else ""
        add(findings, "error", "SIGNATURE_LENGTH",
            f"{alg} signatures are {FIXED_SIGNATURE_SIZES[alg]} bytes; this one is {len(signature)}.{hint}")
    if signature and alg in RSA_SIG_ALGS:
        bits = len(signature) * 8
        result["rsa_modulus_bits"] = bits
        if bits < 2048:
            add(findings, "warning", "RSA_KEY_TOO_SMALL", f"The signature implies a {bits}-bit RSA key; JWA requires 2048 bits or more.")
    if signature and alg in HMAC_HASHES and b64 is not False:
        signing_input = f"{segments[0]}.{segments[1]}".encode("ascii")
        for secret in DEMO_SECRETS:
            mac = hmac.new(secret, signing_input, HMAC_HASHES[alg]).digest()
            if hmac.compare_digest(mac, signature):
                add(findings, "error", "KNOWN_DEMO_SECRET",
                    f"The MAC verifies with the public demo secret {secret.decode()!r} ({len(secret)} bytes). Anyone can forge "
                    "this token. Never accept it; use a random key of at least the hash size.")
                break
    return result


def inspect_jwe(segments: List[str], now: int, findings: List[Finding]) -> Dict[str, Any]:
    header = decode_json_segment(segments[0], "JWE protected header")
    if not isinstance(header, dict):
        raise InputError("JWE protected header is not a JSON object")
    decoded = [b64url_decode(segment) for segment in segments[1:]]
    encrypted_key, iv, ciphertext, tag = decoded
    result: Dict[str, Any] = {
        "kind": "JWE",
        "serialization": "compact",
        "decrypted": False,
        "header": header,
        "segment_bytes": {
            "encrypted_key": len(encrypted_key),
            "iv": len(iv),
            "ciphertext": len(ciphertext),
            "tag": len(tag),
        },
    }
    alg = header.get("alg")
    enc = header.get("enc")
    if not isinstance(alg, str):
        add(findings, "error", "MISSING_ALG", 'The JWE header has no string "alg" member.')
        alg = ""
    elif check_alg_spelling(alg, findings) and alg in JWS_ALGS:
        add(findings, "error", "ALG_KIND_MISMATCH", f'"alg" {alg!r} is a JWS algorithm, but the object has 5 segments (JWE).')
    if not isinstance(enc, str):
        add(findings, "error", "MISSING_ENC", 'A JWE header must contain a string "enc" member.')
        enc = ""
    elif enc not in ENC_PARAMS:
        add(findings, "warning", "UNKNOWN_ENC", f'"enc" {enc!r} is not a registered content encryption algorithm known to this tool.')
    check_common_header(header, findings)

    if alg == "RSA1_5":
        add(findings, "warning", "DEPRECATED_ALG",
            '"RSA1_5" (RSAES-PKCS1-v1_5) is being deprecated (Bleichenbacher-style oracles). Use "RSA-OAEP-256" or ECDH-ES.')
    if alg in EMPTY_KEY_ALGS and encrypted_key:
        add(findings, "error", "ENCRYPTED_KEY_NOT_EMPTY", f'"{alg}" uses direct encryption or key agreement: the encrypted key segment must be empty.')
    if alg and alg not in EMPTY_KEY_ALGS and alg in JWE_ALGS and not encrypted_key:
        add(findings, "error", "ENCRYPTED_KEY_EMPTY", f'"{alg}" wraps or encrypts the CEK: the encrypted key segment must not be empty.')
    if alg in RSA_ENC_ALGS and encrypted_key:
        bits = len(encrypted_key) * 8
        result["rsa_modulus_bits"] = bits
        if bits < 2048:
            add(findings, "warning", "RSA_KEY_TOO_SMALL",
                f"The encrypted key implies a {bits}-bit RSA modulus; JWA requires 2048 bits or more (2048-bit RSA gives 256 bytes).")
    if enc in ENC_PARAMS:
        cek_bytes, iv_bytes, tag_bytes = ENC_PARAMS[enc]
        if len(iv) != iv_bytes:
            add(findings, "error", "IV_LENGTH", f"{enc} requires a {iv_bytes}-byte IV; this one is {len(iv)} bytes.")
        if len(tag) != tag_bytes:
            add(findings, "error", "TAG_LENGTH", f"{enc} produces a {tag_bytes}-byte authentication tag; this one is {len(tag)} bytes.")
        if enc.startswith("A") and "CBC" in enc and (not ciphertext or len(ciphertext) % 16):
            add(findings, "error", "CIPHERTEXT_LENGTH", f"{enc} ciphertext must be a non-empty multiple of 16 bytes.")
        if alg in KEY_WRAP_ALGS and encrypted_key and len(encrypted_key) != cek_bytes + 8:
            add(findings, "error", "ENCRYPTED_KEY_LENGTH",
                f"AES Key Wrap of a {cek_bytes}-byte {enc} CEK gives {cek_bytes + 8} bytes; this one is {len(encrypted_key)}.")
        if alg in GCM_KW_ALGS and encrypted_key and len(encrypted_key) != cek_bytes:
            add(findings, "error", "ENCRYPTED_KEY_LENGTH",
                f"AES GCM key wrap of a {cek_bytes}-byte {enc} CEK gives {cek_bytes} bytes; this one is {len(encrypted_key)}.")
    if alg.startswith("ECDH-ES") and "epk" not in header:
        add(findings, "error", "EPK_MISSING", f'"{alg}" requires the "epk" (ephemeral public key) header parameter.')
    if alg.startswith("ECDH-ES"):
        add(findings, "info", "VALIDATE_EPK", 'The recipient library must check that "epk" is a valid point on the expected curve (invalid-curve attacks).')
    if alg in GCM_KW_ALGS and not ("iv" in header and "tag" in header):
        add(findings, "error", "GCMKW_PARAMS_MISSING", f'"{alg}" requires the "iv" and "tag" header parameters.')
    if alg.startswith("PBES2"):
        add(findings, "info", "PASSWORD_BASED", "PBES2 derives the key from a password; it is still open to offline guessing.")
        p2s = header.get("p2s")
        try:
            salt = b64url_decode(p2s) if isinstance(p2s, str) else b""
        except InputError:
            salt = b""
        if len(salt) < 8:
            add(findings, "error", "PBES2_SALT", '"p2s" must be present and decode to 8 or more bytes.')
        p2c = header.get("p2c")
        if not isinstance(p2c, int) or isinstance(p2c, bool) or p2c < 1:
            add(findings, "error", "PBES2_COUNT", '"p2c" must be a positive integer.')
        elif p2c > 1_200_000:
            add(findings, "warning", "PBES2_COUNT_HIGH",
                f'"p2c" = {p2c}. Cap PBKDF2 iterations (the JWT BCP update suggests rejecting more than 1,200,000) to avoid CPU exhaustion.')
        elif p2c < 1000:
            add(findings, "warning", "PBES2_COUNT_LOW", f'"p2c" = {p2c}; RFC 7518 recommends at least 1000.')
    if "zip" in header:
        add(findings, "warning", "JWE_COMPRESSION",
            '"zip" compression can leak plaintext through ciphertext length and enables decompression bombs. Avoid it, '
            "or cap the decompressed size.")
    replicated = [name for name in ("iss", "sub", "aud") if name in header]
    if replicated:
        add(findings, "info", "REPLICATED_CLAIMS",
            f"Header claims {replicated} are readable without decryption and must match the decrypted claims before use.")
    add(findings, "info", "NOT_DECRYPTED",
        "This tool never decrypts. Decrypting proves confidentiality to the key holder, not who created the token: "
        "anyone with the public key can encrypt. Require an inner signature (nested JWT) when authenticity matters.")
    return result


def check_serialized_header(kind: str, merged: Dict[str, Any], protected: Dict[str, Any], findings: List[Finding]) -> None:
    alg = merged.get("alg")
    if not isinstance(alg, str):
        add(findings, "error", "MISSING_ALG", 'The JOSE header has no string "alg" member.')
    elif check_alg_spelling(alg, findings):
        if kind == "JWS":
            if alg in JWE_ALGS or alg in HPKE_ALGS:
                add(findings, "error", "ALG_KIND_MISMATCH", f'"alg" {alg!r} is a JWE key management algorithm in a JWS.')
            elif alg == "none":
                add(findings, "warning", "ALG_NONE", 'Unsecured JWS ("alg": "none"): no integrity protection.')
            elif alg in HMAC_SIZES:
                add(findings, "info", "SYMMETRIC_ALG", f"{alg} is a MAC: every party that can verify can also create signatures.")
            elif alg == "EdDSA":
                add(findings, "info", "POLYMORPHIC_ALG", '"EdDSA" is deprecated by RFC 9864; prefer "Ed25519" or "Ed448".')
        else:
            if alg in JWS_ALGS:
                add(findings, "error", "ALG_KIND_MISMATCH", f'"alg" {alg!r} is a JWS algorithm in a JWE.')
            elif alg == "RSA1_5":
                add(findings, "warning", "DEPRECATED_ALG", '"RSA1_5" is being deprecated; use "RSA-OAEP-256" or ECDH-ES.')
    if kind == "JWE":
        enc = merged.get("enc")
        if not isinstance(enc, str):
            add(findings, "error", "MISSING_ENC", 'A JWE header must contain a string "enc" member.')
        elif enc not in ENC_PARAMS:
            add(findings, "warning", "UNKNOWN_ENC", f'"enc" {enc!r} is not a registered content encryption algorithm known to this tool.')
        if "zip" in merged:
            add(findings, "warning", "JWE_COMPRESSION", '"zip" compression leaks length information and enables decompression bombs.')
        p2c = merged.get("p2c")
        if isinstance(p2c, int) and not isinstance(p2c, bool) and p2c > 1_200_000:
            add(findings, "warning", "PBES2_COUNT_HIGH", f'"p2c" = {p2c}; cap PBKDF2 iterations to avoid CPU exhaustion.')
    elif "enc" in merged:
        add(findings, "error", "ALG_KIND_MISMATCH", 'A JWS header must not contain "enc"; "enc" marks a JWE.')
    check_common_header(merged, findings)
    for name in ("crit", "b64", "zip"):
        if name in merged and name not in protected:
            add(findings, "error", "MUST_BE_PROTECTED", f'"{name}" must be in the protected header.')
    if merged.get("b64") is False:
        crit = merged.get("crit")
        if not (isinstance(crit, list) and "b64" in crit):
            add(findings, "error", "B64_WITHOUT_CRIT", '"b64": false requires "b64" in "crit" (RFC 7797 Section 6).')
    if "alg" in merged and "alg" not in protected:
        if kind == "JWE":
            add(findings, "info", "UNPROTECTED_ALG",
                '"alg" is in an unprotected header. That is normal for per-recipient key management in the JWE JSON Serialization.')
        else:
            add(findings, "warning", "UNPROTECTED_ALG", '"alg" is only in the unprotected header, so it is not integrity protected.')


def inspect_json_serialization(data: Dict[str, Any], findings: List[Finding]) -> Dict[str, Any]:
    add(findings, "warning", "JSON_SERIALIZATION_NOT_JWT",
        "This is a JOSE JSON Serialization. JWTs always use the Compact Serialization; never read claims from one "
        "representation after verifying another (JWT format confusion).")
    if "ciphertext" in data:
        kind = "JWE"
        serialization = "json-general" if "recipients" in data else "json-flattened"
        entries = data.get("recipients") if serialization == "json-general" else [data]
    elif "payload" in data or "signatures" in data or "signature" in data:
        kind = "JWS"
        serialization = "json-general" if "signatures" in data else "json-flattened"
        entries = data.get("signatures") if serialization == "json-general" else [data]
        if "payload" not in data:
            add(findings, "info", "DETACHED_PAYLOAD", "No \"payload\" member: detached content (RFC 7515 Appendix F).")
    else:
        raise InputError("JSON object is neither a JWS (payload/signatures) nor a JWE (ciphertext) serialization")
    headers = []
    if not isinstance(entries, list) or not entries:
        raise InputError("signatures/recipients must be a non-empty array")
    for entry in entries:
        if not isinstance(entry, dict):
            raise InputError("each signature or recipient must be an object")
        protected: Dict[str, Any] = {}
        source = entry if kind == "JWS" else data
        if "protected" in source:
            if not isinstance(source["protected"], str):
                raise InputError('"protected" must be a base64url string')
            decoded = decode_json_segment(source["protected"], "protected header")
            if not isinstance(decoded, dict):
                raise InputError("protected header is not a JSON object")
            protected = decoded
        shared = data.get("unprotected") if kind == "JWE" and isinstance(data.get("unprotected"), dict) else {}
        per_entry = entry.get("header") if isinstance(entry.get("header"), dict) else {}
        overlap = sorted((set(protected) & set(shared)) | (set(protected) & set(per_entry)) | (set(shared) & set(per_entry)))
        if overlap:
            add(findings, "error", "DUPLICATE_HEADER_PARAMETER", f"Header parameters {overlap} appear in more than one header.")
        merged = {**shared, **per_entry, **protected}
        check_serialized_header(kind, merged, protected, findings)
        headers.append({"protected": protected, "unprotected": {**shared, **per_entry}})
    return {"kind": kind, "serialization": serialization, "verified": False, "headers": headers}


def unencoded_compact_jws(segments: List[str]) -> bool:
    """True for an RFC 7797 compact JWS whose non-detached payload uses printable ASCII other than '.'."""
    if len(segments) != 3 or not SEGMENT_CHARS.match(segments[0]) or not SEGMENT_CHARS.match(segments[2]):
        return False
    if not re.fullmatch(r"[\x20-\x2d\x2f-\x7e]*", segments[1]):
        return False
    try:
        header = decode_json_segment(segments[0], "JOSE header")
    except InputError:
        return False
    return isinstance(header, dict) and header.get("b64") is False


def inspect_token(raw: str, now: int) -> Tuple[Dict[str, Any], List[Finding]]:
    findings: List[Finding] = []
    token = raw.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
        add(findings, "info", "BEARER_PREFIX_REMOVED", 'Removed an HTTP "Bearer " prefix before parsing.')
    if token.startswith("{"):
        try:
            data = strict_json(token)
        except DuplicateKeyError as error:
            raise InputError(f"JSON contains the duplicate member name {error.name!r}") from error
        except ValueError as error:
            raise InputError(f"not valid JSON: {error}") from error
        if not isinstance(data, dict):
            raise InputError("JSON input is not an object")
        return inspect_json_serialization(data, findings), findings
    if not token:
        raise InputError("empty input")
    if not COMPACT_CHARS.match(token):
        if unencoded_compact_jws(token.split(".")):
            return inspect_jws(token.split("."), now, findings), findings
        raise InputError("contains characters other than base64url letters, digits, '-', '_' and '.'; a compact JWS/JWE "
                         "must be rejected (JWT BCP: check JWT format type)")
    segments = token.split(".")
    if len(segments) == 3:
        return inspect_jws(segments, now, findings), findings
    if len(segments) == 5:
        return inspect_jwe(segments, now, findings), findings
    raise InputError(f"{len(segments)} dot-separated segments; a compact JWS has 3 and a compact JWE has 5")


# --------------------------------------------------------------------------- keys


def thumbprint(jwk: Dict[str, Any]) -> Optional[str]:
    """RFC 7638 SHA-256 thumbprint (RFC 9964 members for AKP); None when it cannot be computed."""
    kty = jwk.get("kty")
    members = REQUIRED_MEMBERS.get(kty) if isinstance(kty, str) else None
    if not members or any(not isinstance(jwk.get(name), str) for name in members):
        return None
    canonical = json.dumps({name: jwk[name] for name in members}, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return b64url_encode(hashlib.sha256(canonical.encode("utf-8")).digest())


def b64_len(value: Any) -> Optional[int]:
    if not isinstance(value, str):
        return None
    try:
        return len(b64url_decode(value))
    except InputError:
        return None


def alg_compatibility(jwk: Dict[str, Any], alg: str, findings: List[Finding]) -> None:
    kty = jwk.get("kty")
    crv = jwk.get("crv")
    expected: Optional[str] = None
    if alg in RSA_SIG_ALGS or alg in RSA_ENC_ALGS:
        expected = "RSA"
    elif alg in ALG_EC_CURVE:
        expected = "EC"
        if kty == "EC" and crv != ALG_EC_CURVE[alg]:
            add(findings, "error", "ALG_CURVE_MISMATCH", f'"{alg}" requires crv {ALG_EC_CURVE[alg]!r}, not {crv!r}.')
    elif alg in ("Ed25519", "Ed448"):
        expected = "OKP"
        if kty == "OKP" and crv != alg:
            add(findings, "error", "ALG_CURVE_MISMATCH", f'"{alg}" requires an OKP key with crv {alg!r}, not {crv!r}.')
    elif alg == "EdDSA":
        expected = "OKP"
        if kty == "OKP" and crv not in ("Ed25519", "Ed448"):
            add(findings, "error", "ALG_CURVE_MISMATCH", '"EdDSA" requires crv "Ed25519" or "Ed448".')
    elif alg.startswith("ECDH-ES"):
        if kty == "OKP" and crv not in ("X25519", "X448"):
            add(findings, "error", "ALG_CURVE_MISMATCH", "ECDH-ES with OKP keys requires crv X25519 or X448.")
        if kty not in ("EC", "OKP"):
            add(findings, "error", "ALG_KTY_MISMATCH", f'"{alg}" requires an EC or OKP key, not {kty!r}.')
        return
    elif alg in HMAC_SIZES or alg in OCT_EXACT_BYTES or alg == "dir" or alg.startswith("PBES2"):
        expected = "oct"
    elif alg.startswith("ML-DSA"):
        expected = "AKP"
    if expected and kty != expected:
        add(findings, "error", "ALG_KTY_MISMATCH", f'"{alg}" requires kty {expected!r}, not {kty!r}.')


def inspect_key(jwk: Any, in_set: bool) -> Dict[str, Any]:
    findings: List[Finding] = []
    summary: Dict[str, Any] = {"findings": findings}
    if not isinstance(jwk, dict):
        add(findings, "error", "NOT_AN_OBJECT", "A JWK must be a JSON object.")
        return summary
    kty = jwk.get("kty")
    for name in ("kid", "kty", "alg", "use", "key_ops", "crv"):
        if name in jwk:
            summary[name] = jwk[name]
    if not isinstance(kty, str):
        add(findings, "error", "KTY_MISSING", 'Every JWK needs a string "kty".')
        return summary
    if kty not in REQUIRED_MEMBERS:
        add(findings, "warning", "UNKNOWN_KTY", f'Unknown "kty" {kty!r}; RFC 7517 says recipients should ignore such keys in a set.')
        return summary
    missing = [name for name in REQUIRED_MEMBERS[kty] if name not in jwk]
    if missing:
        add(findings, "error", "REQUIRED_MEMBER_MISSING", f"{kty} keys require {list(REQUIRED_MEMBERS[kty])}; missing {missing}.")
    private = [name for name in PRIVATE_MEMBERS[kty] if name in jwk]
    summary["private"] = bool(private)
    if private:
        if kty == "oct":
            message = 'An "oct" key is a shared secret. Never publish it in a JWK Set or send it to clients.'
        else:
            message = f"Private key members {private} are present (values not printed). Never publish them."
        add(findings, "error" if in_set else "warning", "PRIVATE_KEY_MATERIAL",
            message + (" A JWK Set endpoint must only contain public keys." if in_set else
                       " Store private JWKs encrypted at rest (for example as a JWE with cty \"jwk+json\")."))

    if kty == "RSA":
        n_len = b64_len(jwk.get("n"))
        if n_len:
            raw_n = b64url_decode(jwk["n"])
            bits = int.from_bytes(raw_n, "big").bit_length()
            summary["bits"] = bits
            if bits < 2048:
                add(findings, "error", "RSA_KEY_TOO_SMALL", f"RSA modulus is {bits} bits; JWA requires 2048 bits or more.")
            if raw_n[:1] == b"\x00":
                add(findings, "warning", "NON_MINIMAL_ENCODING", '"n" has a leading zero byte; Base64urlUInt must use the minimum number of octets.')
    elif kty == "EC":
        size = EC_COORDINATE_BYTES.get(text_value(jwk.get("crv")) or "")
        if size is None:
            add(findings, "warning", "UNKNOWN_CURVE", f'Unknown EC "crv" {jwk.get("crv")!r}.')
        else:
            for name in ("x", "y", "d"):
                length = b64_len(jwk.get(name))
                if name in jwk and length != size:
                    add(findings, "error", "COORDINATE_LENGTH", f'"{name}" must be exactly {size} bytes for {jwk["crv"]}; got {length}.')
    elif kty == "OKP":
        size = OKP_KEY_BYTES.get(text_value(jwk.get("crv")) or "")
        if size is None:
            add(findings, "warning", "UNKNOWN_CURVE", f'Unknown OKP "crv" {jwk.get("crv")!r}.')
        else:
            for name in ("x", "d"):
                length = b64_len(jwk.get(name))
                if name in jwk and length != size:
                    add(findings, "error", "KEY_LENGTH", f'"{name}" must be {size} bytes for {jwk["crv"]}; got {length}.')
    elif kty == "oct":
        length = b64_len(jwk.get("k"))
        if length is not None:
            summary["bits"] = length * 8
            alg = text_value(jwk.get("alg"))
            if alg in HMAC_SIZES and length < HMAC_SIZES[alg]:
                add(findings, "error", "KEY_TOO_SHORT", f"{alg} needs a key of at least {HMAC_SIZES[alg]} bytes; this one is {length}.")
            elif alg in OCT_EXACT_BYTES and length != OCT_EXACT_BYTES[alg]:
                add(findings, "error", "KEY_LENGTH", f"{alg} needs a {OCT_EXACT_BYTES[alg]}-byte key; this one is {length}.")
            elif "alg" not in jwk and length < 32:
                add(findings, "warning", "KEY_TOO_SHORT", f"Symmetric key is {length} bytes; HS256 needs at least 32 random bytes.")

    alg = jwk.get("alg")
    if alg is None:
        add(findings, "info", "ALG_MISSING",
            'No "alg": bind each key to exactly one algorithm, here or in verifier configuration (JWT BCP).')
    elif not isinstance(alg, str):
        add(findings, "error", "ALG_NOT_STRING", '"alg" must be a string.')
    else:
        alg_compatibility(jwk, alg, findings)
        if alg == "EdDSA":
            add(findings, "info", "POLYMORPHIC_ALG", '"EdDSA" is deprecated by RFC 9864; prefer "Ed25519" or "Ed448".')
        if alg == "RSA1_5":
            add(findings, "warning", "DEPRECATED_ALG", '"RSA1_5" is being deprecated; prefer "RSA-OAEP-256".')

    use = jwk.get("use")
    key_ops = jwk.get("key_ops")
    if use is not None and use not in ("sig", "enc"):
        add(findings, "warning", "UNKNOWN_USE", f'"use" {use!r} is not "sig" or "enc".')
    if use is not None and key_ops is not None:
        add(findings, "warning", "USE_AND_KEY_OPS", '"use" and "key_ops" should not be used together (RFC 7517 Section 4.3).')
        if isinstance(key_ops, list) and all(isinstance(op, str) for op in key_ops):
            signing_ops = {"sign", "verify"}
            if (use == "sig" and not set(key_ops) <= signing_ops) or (use == "enc" and set(key_ops) & signing_ops):
                add(findings, "error", "USE_KEY_OPS_CONFLICT", f'"use" {use!r} conflicts with "key_ops" {key_ops}.')
    if isinstance(alg, str) and use is not None:
        if alg in SIGNING_ALGS and use == "enc":
            add(findings, "error", "USE_ALG_CONFLICT", f'"use": "enc" conflicts with the signing algorithm {alg!r}.')
        if (alg in JWE_ALGS or alg in HPKE_ALGS) and use == "sig":
            add(findings, "error", "USE_ALG_CONFLICT", f'"use": "sig" conflicts with the key management algorithm {alg!r}.')
    if "x5c" in jwk:
        chain = jwk["x5c"]
        if not isinstance(chain, list) or not chain:
            add(findings, "error", "X5C_INVALID", '"x5c" must be a non-empty array of base64 DER certificates.')
        elif any(not isinstance(cert, str) or "-" in cert or "_" in cert for cert in chain):
            add(findings, "error", "X5C_ENCODING", '"x5c" entries are standard base64 (not base64url) DER certificates.')

    tp = thumbprint(jwk)
    if tp:
        summary["thumbprint_sha256"] = tp
        summary["thumbprint_uri"] = f"urn:ietf:params:oauth:jwk-thumbprint:sha-256:{tp}"
        if jwk.get("kid") == tp:
            add(findings, "info", "KID_IS_THUMBPRINT", '"kid" equals the RFC 7638 thumbprint.')
    return summary


def inspect_jwk_document(text: str) -> Tuple[Dict[str, Any], List[Finding]]:
    findings: List[Finding] = []
    try:
        data = strict_json(text)
    except DuplicateKeyError as error:
        raise InputError(f"JSON contains the duplicate member name {error.name!r}") from error
    except ValueError as error:
        raise InputError(f"not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise InputError("a JWK or JWK Set must be a JSON object")
    if "keys" in data:
        if not isinstance(data["keys"], list):
            raise InputError('a JWK Set "keys" member must be an array')
        keys = [inspect_key(item, in_set=True) for item in data["keys"]]
        for index, key in enumerate(keys):
            key["index"] = index
        kids: Dict[str, List[Any]] = {}
        for key in keys:
            if isinstance(key.get("kid"), str):
                kids.setdefault(key["kid"], []).append(text_value(key.get("kty")))
        duplicates = sorted(kid for kid, ktys in kids.items() if len(ktys) > 1 and len(set(ktys)) == 1)
        if duplicates:
            add(findings, "warning", "DUPLICATE_KID", f"Keys of the same type share kid values {duplicates}; verifiers cannot pick the right key.")
        if len(keys) > 1 and any("kid" not in key for key in keys):
            add(findings, "warning", "KID_MISSING", 'A JWK Set with several keys should give every key a distinct "kid".')
        if not keys:
            add(findings, "warning", "EMPTY_SET", "The JWK Set contains no keys.")
        return {"kind": "JWK Set", "keys": keys}, findings
    if "kty" not in data:
        raise InputError('JSON object has neither "kty" (JWK) nor "keys" (JWK Set)')
    key = inspect_key(data, in_set=False)
    return {"kind": "JWK", "keys": [key]}, findings


# --------------------------------------------------------------------------- CLI


def all_findings(result: Dict[str, Any], findings: List[Finding]) -> List[Finding]:
    collected = list(findings)
    for key in result.get("keys", []):
        collected.extend(key.get("findings", []))
    return collected


def read_input(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    return value


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only JOSE token and JWK inspector (never verifies or decrypts).")
    sub = parser.add_subparsers(dest="command", required=True)
    token_parser = sub.add_parser("token", help="decode and lint a compact or JSON-serialized JWS/JWE/JWT")
    token_parser.add_argument("value", help="the token, or - to read it from stdin")
    token_parser.add_argument("--now", type=int, default=None, help="epoch seconds used for exp/nbf/iat checks")
    jwk_parser = sub.add_parser("jwk", help="lint a JWK or JWK Set file")
    jwk_parser.add_argument("path", help="path to a JSON file, or - to read from stdin")
    args = parser.parse_args(argv)

    try:
        if args.command == "token":
            now = args.now if args.now is not None else int(time.time())
            result, findings = inspect_token(read_input(args.value), now)
        else:
            if args.path == "-":
                text = sys.stdin.read()
            else:
                with open(args.path, "rb") as handle:
                    try:
                        text = handle.read().decode("utf-8")
                    except UnicodeDecodeError as error:
                        raise InputError("file is not UTF-8 JSON") from error
            result, findings = inspect_jwk_document(text)
    except (InputError, OSError) as error:
        print(json.dumps({"error": str(error)}, indent=2))
        return 2
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        print(json.dumps({"error": f"could not process input ({type(error).__name__}): {error}"}, indent=2))
        return 2

    result["findings"] = findings
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    levels = {finding["level"] for finding in all_findings(result, findings)}
    return 1 if levels & {"warning", "error"} else 0


if __name__ == "__main__":
    sys.exit(main())
