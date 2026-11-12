#!/usr/bin/env python3
"""Self-tests for jose_inspect.py. Run: python -B scripts/test_jose_inspect.py

Uses RFC test vectors from assets/test-vectors.json (extracted programmatically
from RFC 7515, 7516, 7517, 7520, 7638, and 8037) plus crafted attack-shaped tokens.
Standard library only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import jose_inspect  # noqa: E402

VECTORS: Dict[str, Any] = json.loads((SCRIPTS.parent / "assets" / "test-vectors.json").read_text(encoding="utf-8"))
NOW = 1_300_819_370  # just before "exp": 1300819380 in the RFC 7515 examples


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64json(value: Any) -> str:
    return b64(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def make_jws(header: Dict[str, Any], claims: Any, signature: bytes = b"\x01" * 64) -> str:
    payload = claims if isinstance(claims, str) else b64json(claims)
    return f"{b64json(header)}.{payload}.{b64(signature)}"


def make_jwe(header: Dict[str, Any], key: bytes, iv: bytes, ciphertext: bytes, tag: bytes) -> str:
    return ".".join([b64json(header), b64(key), b64(iv), b64(ciphertext), b64(tag)])


def run_cli(args: List[str]) -> Tuple[int, Dict[str, Any]]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = jose_inspect.main(args)
    return code, json.loads(buffer.getvalue())


def codes(result: Dict[str, Any]) -> List[str]:
    return [finding["code"] for finding in result.get("findings", [])]


def level_of(result: Dict[str, Any], code: str) -> Optional[str]:
    for finding in result.get("findings", []):
        if finding["code"] == code:
            return finding["level"]
    return None


GOOD_CLAIMS = {"iss": "https://issuer.example.com/", "sub": "user-123", "aud": "https://api.example.com",
               "iat": NOW - 10, "exp": NOW + 600}


class RfcJwsVectors(unittest.TestCase):
    def test_rfc7515_a1_hs256(self) -> None:
        code, result = run_cli(["token", VECTORS["jws"]["rfc7515-a1-hs256"]["token"], "--now", str(NOW)])
        self.assertEqual(code, 1)  # AUD_MISSING warning
        self.assertEqual(result["kind"], "JWS")
        self.assertFalse(result["verified"])
        self.assertEqual(result["header"], {"typ": "JWT", "alg": "HS256"})
        self.assertEqual(result["claims"]["iss"], "joe")
        self.assertTrue(result["claims"]["http://example.com/is_root"])
        self.assertEqual(result["signature_bytes"], 32)
        self.assertIn("SYMMETRIC_ALG", codes(result))
        self.assertIn("TYP_JWT_NOT_EXPLICIT", codes(result))
        self.assertNotIn("EXPIRED", codes(result))
        self.assertNotIn("KNOWN_DEMO_SECRET", codes(result))

    def test_rfc7515_a1_expired_later(self) -> None:
        _, result = run_cli(["token", VECTORS["jws"]["rfc7515-a1-hs256"]["token"], "--now", "1700000000"])
        self.assertIn("EXPIRED", codes(result))

    def test_signature_sizes_of_rfc_vectors(self) -> None:
        expected = {"rfc7515-a2-rs256": 256, "rfc7515-a3-es256": 64, "rfc7515-a4-es512": 132,
                    "rfc7520-4.2-ps384": 256, "rfc7520-4.3-es512": 132, "rfc7520-4.4-hs256": 32}
        for name, size in expected.items():
            with self.subTest(name=name):
                _, result = run_cli(["token", VECTORS["jws"][name]["token"], "--now", str(NOW)])
                self.assertEqual(result["signature_bytes"], size)
                self.assertNotIn("SIGNATURE_LENGTH", codes(result))
                self.assertNotIn("RSA_KEY_TOO_SMALL", codes(result))

    def test_rfc7515_a5_unsecured(self) -> None:
        code, result = run_cli(["token", VECTORS["jws"]["rfc7515-a5-none"]["token"], "--now", str(NOW)])
        self.assertEqual(code, 1)
        self.assertEqual(result["signature_bytes"], 0)
        self.assertEqual(level_of(result, "ALG_NONE"), "warning")
        self.assertNotIn("EMPTY_SIGNATURE", codes(result))

    def test_rfc7520_non_json_payload(self) -> None:
        _, result = run_cli(["token", VECTORS["jws"]["rfc7520-4.1-rs256"]["token"]])
        self.assertIn("PAYLOAD_NOT_JSON", codes(result))
        self.assertIn("payload_text", result)
        self.assertNotIn("claims", result)

    def test_all_rfc_jws_vectors_have_no_errors(self) -> None:
        for name, vector in VECTORS["jws"].items():
            with self.subTest(name=name):
                _, result = run_cli(["token", vector["token"], "--now", str(NOW)])
                self.assertEqual([c for c in codes(result) if level_of(result, c) == "error"], [])


class RfcJweVectors(unittest.TestCase):
    def test_rfc7516_a1_sizes(self) -> None:
        code, result = run_cli(["token", VECTORS["jwe"]["rfc7516-a1-rsa-oaep-a256gcm"]["token"]])
        self.assertEqual(code, 0)
        self.assertEqual(result["kind"], "JWE")
        self.assertFalse(result["decrypted"])
        self.assertEqual(result["header"], {"alg": "RSA-OAEP", "enc": "A256GCM"})
        self.assertEqual(result["segment_bytes"], {"encrypted_key": 256, "iv": 12, "ciphertext": 63, "tag": 16})
        self.assertEqual(result["rsa_modulus_bits"], 2048)

    def test_rfc7516_a2_rsa1_5_deprecated(self) -> None:
        _, result = run_cli(["token", VECTORS["jwe"]["rfc7516-a2-rsa1_5-a128cbc-hs256"]["token"]])
        self.assertEqual(level_of(result, "DEPRECATED_ALG"), "warning")
        self.assertEqual(result["segment_bytes"]["iv"], 16)

    def test_rfc7516_a3_key_wrap_length(self) -> None:
        _, result = run_cli(["token", VECTORS["jwe"]["rfc7516-a3-a128kw-a128cbc-hs256"]["token"]])
        self.assertEqual(result["segment_bytes"]["encrypted_key"], 40)
        self.assertNotIn("ENCRYPTED_KEY_LENGTH", codes(result))

    def test_rfc7520_modes(self) -> None:
        cases = {
            "rfc7520-5.3-pbes2": ("PASSWORD_BASED", None),
            "rfc7520-5.4-ecdh-es-a128kw": ("VALIDATE_EPK", 24),
            "rfc7520-5.5-ecdh-es": ("VALIDATE_EPK", 0),
            "rfc7520-5.6-dir": (None, 0),
            "rfc7520-5.7-a256gcmkw": (None, 32),
            "rfc7520-5.9-a128kw-zip": ("JWE_COMPRESSION", 24),
            "rfc7520-6.8-nested-outer": ("NESTED_JWT", 512),
        }
        for name, (expected_code, key_bytes) in cases.items():
            with self.subTest(name=name):
                _, result = run_cli(["token", VECTORS["jwe"][name]["token"]])
                if expected_code:
                    self.assertIn(expected_code, codes(result))
                if key_bytes is not None:
                    self.assertEqual(result["segment_bytes"]["encrypted_key"], key_bytes)

    def test_all_rfc_jwe_vectors_have_no_errors(self) -> None:
        for name, vector in VECTORS["jwe"].items():
            with self.subTest(name=name):
                _, result = run_cli(["token", vector["token"]])
                self.assertEqual([c for c in codes(result) if level_of(result, c) == "error"], [])
                self.assertIn("NOT_DECRYPTED", codes(result))


class ArticleSamples(unittest.TestCase):
    def test_article_jws_uses_public_demo_secret(self) -> None:
        code, result = run_cli(["token", VECTORS["article"]["jws"]["token"]])
        self.assertEqual(code, 1)
        self.assertEqual(result["claims"], {"sub": "1234567890", "name": "John Doe", "iat": 1516239022})
        self.assertEqual(level_of(result, "KNOWN_DEMO_SECRET"), "error")
        for code_name in ("EXP_MISSING", "ISS_MISSING", "AUD_MISSING"):
            self.assertIn(code_name, codes(result))

    def test_article_jwe_is_illustrative_only(self) -> None:
        _, result = run_cli(["token", VECTORS["article"]["jwe"]["token"]])
        self.assertEqual(result["segment_bytes"], {"encrypted_key": 95, "iv": 16, "ciphertext": 16, "tag": 16})
        self.assertEqual(level_of(result, "IV_LENGTH"), "error")
        self.assertEqual(level_of(result, "RSA_KEY_TOO_SMALL"), "warning")


class CraftedTokens(unittest.TestCase):
    def test_good_typed_token_has_no_warnings(self) -> None:
        token = make_jws({"alg": "ES256", "kid": "k1", "typ": "at+jwt"}, GOOD_CLAIMS)
        code, result = run_cli(["token", token, "--now", str(NOW)])
        self.assertEqual(code, 0, result["findings"])
        self.assertIn("TYP_PROFILE", codes(result))

    def test_bearer_prefix_and_whitespace(self) -> None:
        token = make_jws({"alg": "ES256", "kid": "k1", "typ": "at+jwt"}, GOOD_CLAIMS)
        code, result = run_cli(["token", f"  Bearer {token}\n", "--now", str(NOW)])
        self.assertEqual(code, 0)
        self.assertIn("BEARER_PREFIX_REMOVED", codes(result))

    def test_alg_case_variant(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "nOnE"}, GOOD_CLAIMS, b""), "--now", str(NOW)])
        self.assertEqual(level_of(result, "ALG_CASE_VARIANT"), "error")

    def test_unknown_alg(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "XS999"}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertEqual(level_of(result, "UNKNOWN_ALG"), "warning")

    def test_none_with_signature(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "none"}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertIn("NONE_WITH_SIGNATURE", codes(result))

    def test_empty_signature(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "RS256"}, GOOD_CLAIMS, b""), "--now", str(NOW)])
        self.assertIn("EMPTY_SIGNATURE", codes(result))

    def test_der_encoded_ecdsa_signature(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "ES256"}, GOOD_CLAIMS, b"\x30" * 71), "--now", str(NOW)])
        self.assertEqual(level_of(result, "SIGNATURE_LENGTH"), "error")
        self.assertIn("R || S", next(f["message"] for f in result["findings"] if f["code"] == "SIGNATURE_LENGTH"))

    def test_small_rsa_signature(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "RS256"}, GOOD_CLAIMS, b"\x01" * 128), "--now", str(NOW)])
        self.assertEqual(result["rsa_modulus_bits"], 1024)
        self.assertIn("RSA_KEY_TOO_SMALL", codes(result))

    def test_jwe_alg_in_jws(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "RSA-OAEP", "enc": "A256GCM"}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertIn("ALG_KIND_MISMATCH", codes(result))

    def test_remote_and_embedded_keys(self) -> None:
        header = {"alg": "RS256", "jku": "https://attacker.example/jwks.json", "x5u": "https://attacker.example/c.pem",
                  "jwk": {"kty": "oct", "k": "AA"}, "x5c": ["MIIB"]}
        _, result = run_cli(["token", make_jws(header, GOOD_CLAIMS, b"\x01" * 256), "--now", str(NOW)])
        self.assertEqual(codes(result).count("REMOTE_KEY_URL"), 2)
        self.assertIn("EMBEDDED_JWK", codes(result))
        self.assertIn("X5C_PRESENT", codes(result))

    def test_suspicious_kid(self) -> None:
        for kid in ("../../dev/null", "x' UNION SELECT 'k", "a b"):
            with self.subTest(kid=kid):
                _, result = run_cli(["token", make_jws({"alg": "ES256", "kid": kid}, GOOD_CLAIMS), "--now", str(NOW)])
                self.assertIn("SUSPICIOUS_KID", codes(result))
        _, result = run_cli(["token", make_jws({"alg": "ES256", "kid": "2026-11_sig.v1"}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertNotIn("SUSPICIOUS_KID", codes(result))

    def test_crit_rules(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "ES256", "crit": []}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertIn("CRIT_INVALID", codes(result))
        _, result = run_cli(["token", make_jws({"alg": "ES256", "crit": ["exp"]}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertIn("CRIT_INVALID", codes(result))
        _, result = run_cli(["token", make_jws({"alg": "ES256", "crit": ["alg"]}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertIn("CRIT_INVALID", codes(result))
        _, result = run_cli(["token", make_jws({"alg": "ES256", "crit": ["exp"], "exp": 1}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertNotIn("CRIT_INVALID", codes(result))
        self.assertIn("CRIT_PRESENT", codes(result))

    def test_b64_false_requires_crit(self) -> None:
        token = f"{b64json({'alg': 'HS256', 'b64': False})}.$.02.{b64(b'0' * 32)}"
        code, result = run_cli(["token", token])
        self.assertEqual(code, 2)  # "$" is not a legal compact character
        token = f"{b64json({'alg': 'HS256', 'b64': False})}.payload.{b64(b'0' * 32)}"
        _, result = run_cli(["token", token])
        self.assertIn("B64_WITHOUT_CRIT", codes(result))
        token = f"{b64json({'alg': 'HS256', 'b64': False, 'crit': ['b64']})}.payload.{b64(b'0' * 32)}"
        _, result = run_cli(["token", token])
        self.assertNotIn("B64_WITHOUT_CRIT", codes(result))
        self.assertIn("UNENCODED_PAYLOAD", codes(result))

    def test_claim_checks(self) -> None:
        claims = dict(GOOD_CLAIMS, exp=(NOW + 600) * 1000)
        _, result = run_cli(["token", make_jws({"alg": "ES256"}, claims), "--now", str(NOW)])
        self.assertIn("TIMESTAMP_MILLISECONDS", codes(result))
        _, result = run_cli(["token", make_jws({"alg": "ES256"}, dict(GOOD_CLAIMS, exp="tomorrow")), "--now", str(NOW)])
        self.assertEqual(level_of(result, "CLAIM_TYPE"), "error")
        _, result = run_cli(["token", make_jws({"alg": "ES256"}, dict(GOOD_CLAIMS, nbf=NOW + 3600)), "--now", str(NOW)])
        self.assertIn("NOT_YET_VALID", codes(result))
        _, result = run_cli(["token", make_jws({"alg": "ES256"}, dict(GOOD_CLAIMS, aud=["a", 1])), "--now", str(NOW)])
        self.assertIn("CLAIM_TYPE", codes(result))
        _, result = run_cli(["token", make_jws({"alg": "ES256"}, dict(GOOD_CLAIMS, iat=NOW - 10, exp=NOW + 7 * 86400)), "--now", str(NOW)])
        self.assertIn("LONG_LIFETIME", codes(result))

    def test_sensitive_claims_in_jws(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "ES256"}, dict(GOOD_CLAIMS, password="hunter2")), "--now", str(NOW)])
        self.assertIn("SENSITIVE_DATA_IN_JWS", codes(result))

    def test_duplicate_claim_and_header(self) -> None:
        header = b64json({"alg": "ES256"})
        payload = b64(b'{"sub":"user","sub":"admin"}')
        _, result = run_cli(["token", f"{header}.{payload}.{b64(b'1' * 64)}"])
        self.assertIn("DUPLICATE_CLAIM", codes(result))
        dup_header = b64(b'{"alg":"none","alg":"ES256"}')
        code, result = run_cli(["token", f"{dup_header}.{payload}.{b64(b'1' * 64)}"])
        self.assertEqual(code, 2)
        self.assertIn("duplicate", result["error"])

    def test_known_demo_secret_detection(self) -> None:
        header, payload = b64json({"alg": "HS512"}), b64json({"sub": "x"})
        mac = hmac.new(b"your-512-bit-secret", f"{header}.{payload}".encode(), hashlib.sha512).digest()
        _, result = run_cli(["token", f"{header}.{payload}.{b64(mac)}"])
        self.assertIn("KNOWN_DEMO_SECRET", codes(result))
        random_mac = hmac.new(b"x" * 64, f"{header}.{payload}".encode(), hashlib.sha512).digest()
        _, result = run_cli(["token", f"{header}.{payload}.{b64(random_mac)}"])
        self.assertNotIn("KNOWN_DEMO_SECRET", codes(result))

    def test_nested_cty(self) -> None:
        inner = make_jws({"alg": "ES256", "typ": "at+jwt"}, GOOD_CLAIMS)
        token = f"{b64json({'alg': 'ES256', 'cty': 'JWT'})}.{b64(inner.encode())}.{b64(b'1' * 64)}"
        _, result = run_cli(["token", token])
        self.assertIn("NESTED_JWT", codes(result))
        self.assertTrue(result["payload_text"].startswith("eyJ"))


class CraftedJwe(unittest.TestCase):
    def test_dir_with_encrypted_key(self) -> None:
        token = make_jwe({"alg": "dir", "enc": "A256GCM"}, b"\x01" * 32, b"\x02" * 12, b"\x03" * 20, b"\x04" * 16)
        _, result = run_cli(["token", token])
        self.assertIn("ENCRYPTED_KEY_NOT_EMPTY", codes(result))

    def test_key_wrap_without_encrypted_key(self) -> None:
        token = make_jwe({"alg": "A256KW", "enc": "A256GCM"}, b"", b"\x02" * 12, b"\x03" * 20, b"\x04" * 16)
        _, result = run_cli(["token", token])
        self.assertIn("ENCRYPTED_KEY_EMPTY", codes(result))

    def test_lengths(self) -> None:
        token = make_jwe({"alg": "A128KW", "enc": "A256CBC-HS512"}, b"\x01" * 40, b"\x02" * 16, b"\x03" * 30, b"\x04" * 16)
        _, result = run_cli(["token", token])
        for code_name in ("TAG_LENGTH", "CIPHERTEXT_LENGTH", "ENCRYPTED_KEY_LENGTH"):
            self.assertIn(code_name, codes(result))

    def test_pbes2_limits(self) -> None:
        base = {"alg": "PBES2-HS256+A128KW", "enc": "A128GCM", "p2s": b64(b"salt-123")}
        high = make_jwe(dict(base, p2c=10_000_000), b"\x01" * 24, b"\x02" * 12, b"\x03" * 5, b"\x04" * 16)
        _, result = run_cli(["token", high])
        self.assertIn("PBES2_COUNT_HIGH", codes(result))
        low = make_jwe(dict(base, p2c=10, p2s=b64(b"s")), b"\x01" * 24, b"\x02" * 12, b"\x03" * 5, b"\x04" * 16)
        _, result = run_cli(["token", low])
        self.assertIn("PBES2_COUNT_LOW", codes(result))
        self.assertIn("PBES2_SALT", codes(result))

    def test_ecdh_es_requires_epk_and_gcmkw_params(self) -> None:
        _, result = run_cli(["token", make_jwe({"alg": "ECDH-ES", "enc": "A128GCM"}, b"", b"\x02" * 12, b"\x03", b"\x04" * 16)])
        self.assertIn("EPK_MISSING", codes(result))
        _, result = run_cli(["token", make_jwe({"alg": "A128GCMKW", "enc": "A128GCM"}, b"\x01" * 16, b"\x02" * 12, b"\x03", b"\x04" * 16)])
        self.assertIn("GCMKW_PARAMS_MISSING", codes(result))

    def test_missing_enc_and_jws_alg(self) -> None:
        _, result = run_cli(["token", make_jwe({"alg": "HS256"}, b"", b"", b"\x03", b"")])
        self.assertIn("MISSING_ENC", codes(result))
        self.assertIn("ALG_KIND_MISMATCH", codes(result))

    def test_replicated_claims(self) -> None:
        token = make_jwe({"alg": "dir", "enc": "A128GCM", "iss": "https://issuer.example.com/"}, b"", b"\x02" * 12, b"\x03", b"\x04" * 16)
        _, result = run_cli(["token", token])
        self.assertIn("REPLICATED_CLAIMS", codes(result))


class Serializations(unittest.TestCase):
    def test_flattened_json_jws(self) -> None:
        flattened = {"payload": b64json(GOOD_CLAIMS), "protected": b64json({"alg": "ES256"}), "signature": b64(b"1" * 64)}
        code, result = run_cli(["token", json.dumps(flattened)])
        self.assertEqual(code, 1)
        self.assertEqual((result["kind"], result["serialization"]), ("JWS", "json-flattened"))
        self.assertIn("JSON_SERIALIZATION_NOT_JWT", codes(result))

    def test_general_json_jws_unprotected_alg(self) -> None:
        general = {"payload": b64json(GOOD_CLAIMS), "signatures": [{"header": {"alg": "ES256"}, "signature": b64(b"1" * 64)}]}
        _, result = run_cli(["token", json.dumps(general)])
        self.assertEqual(result["serialization"], "json-general")
        self.assertIn("UNPROTECTED_ALG", codes(result))

    def test_json_jwe_duplicate_parameter(self) -> None:
        flattened = {"protected": b64json({"alg": "dir", "enc": "A128GCM"}), "unprotected": {"enc": "A256GCM"},
                     "iv": b64(b"\x02" * 12), "ciphertext": b64(b"\x03"), "tag": b64(b"\x04" * 16)}
        _, result = run_cli(["token", json.dumps(flattened)])
        self.assertEqual((result["kind"], result["serialization"]), ("JWE", "json-flattened"))
        self.assertIn("DUPLICATE_HEADER_PARAMETER", codes(result))

    def test_rejects_non_jose_input(self) -> None:
        for value in ("not-a-token", "a.b", "a.b.c.d", '{"alg":"none"}.e30.', "", "{]"):
            with self.subTest(value=value):
                code, result = run_cli(["token", value])
                self.assertEqual(code, 2)
                self.assertIn("error", result)

    def test_invalid_base64url_length(self) -> None:
        code, result = run_cli(["token", f"{b64json({'alg': 'ES256'})}.A.{b64(b'1' * 64)}"])
        self.assertEqual(code, 2)


class RfcJsonSerializations(unittest.TestCase):
    def test_rfc_json_vectors(self) -> None:
        expected = {
            "rfc7515-a6-general-jws": ("JWS", "json-general"),
            "rfc7515-a7-flattened-jws": ("JWS", "json-flattened"),
            "rfc7516-a4-general-jwe": ("JWE", "json-general"),
            "rfc7516-a5-flattened-jwe": ("JWE", "json-flattened"),
        }
        for name, (kind, serialization) in expected.items():
            with self.subTest(name=name):
                code, result = run_cli(["token", json.dumps(VECTORS["json_serializations"][name]["json"])])
                self.assertEqual(code, 1)  # JSON_SERIALIZATION_NOT_JWT is always a warning
                self.assertEqual((result["kind"], result["serialization"]), (kind, serialization))
                self.assertEqual([f["code"] for f in result["findings"] if f["level"] == "error"], [])

    def test_per_recipient_alg_is_info_for_jwe(self) -> None:
        _, result = run_cli(["token", json.dumps(VECTORS["json_serializations"]["rfc7516-a4-general-jwe"]["json"])])
        self.assertEqual({f["level"] for f in result["findings"] if f["code"] == "UNPROTECTED_ALG"}, {"info"})
        self.assertIn("DEPRECATED_ALG", codes(result))  # the first recipient uses RSA1_5


class ReviewRegressions(unittest.TestCase):
    """Edge cases found in an independent review on 2026-11-12."""

    def jwk(self, text: str) -> Tuple[int, Dict[str, Any]]:
        stdin = sys.stdin
        sys.stdin = io.StringIO(text)
        try:
            return run_cli(["jwk", "-"])
        finally:
            sys.stdin = stdin

    def test_unhashable_jwk_values_do_not_crash(self) -> None:
        for text in ('{"kty":"EC","crv":[],"x":"AA","y":"AA"}', '{"kty":"OKP","crv":{},"x":"AA"}',
                     '{"kty":"oct","k":"AAAA","alg":["HS256"]}', '{"kty":"EC","crv":"P-256","x":"AA","y":"AA","use":"sig","key_ops":[[]]}',
                     '{"keys":[{"kty":[],"kid":"a"},{"kty":[],"kid":"a"}]}', '{"kty":[]}'):
            with self.subTest(text=text):
                code, result = self.jwk(text)
                self.assertIn(code, (0, 1, 2))
                self.assertTrue("keys" in result or "error" in result)

    def test_non_finite_and_huge_numbers(self) -> None:
        header = b64json({"alg": "ES256"})
        for payload, expected in ((b'{"nbf":Infinity}', "INVALID_CLAIMS_JSON"), (b'{"exp":-1e400}', "INVALID_CLAIMS_JSON"),
                                  (b'{"iat":1e400}', "INVALID_CLAIMS_JSON"), (b'{"exp":NaN}', "INVALID_CLAIMS_JSON"),
                                  (b'{"exp":1' + b"0" * 400 + b',"iat":0}', "CLAIM_TYPE")):
            with self.subTest(payload=payload[:20]):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = jose_inspect.main(["token", f"{header}.{b64(payload)}.{b64(b'1' * 64)}"])
                result = json.loads(buffer.getvalue(), parse_constant=self.reject_constant)  # output is strict JSON
                self.assertEqual(code, 1)
                self.assertIn(expected, codes(result))
                self.assertNotIn("PAYLOAD_NOT_JSON", codes(result))

    @staticmethod
    def reject_constant(name: str) -> Any:
        raise AssertionError(f"inspector emitted the non-JSON constant {name}")

    def test_nan_in_header_and_deep_nesting(self) -> None:
        nan_header = b64(b'{"alg":NaN}')
        code, _ = run_cli(["token", f"{nan_header}.{b64json({})}.{b64(b'1' * 64)}"])
        self.assertEqual(code, 2)
        deep = b'{"alg":"ES256","x":' + b"[" * 200_000 + b"]" * 200_000 + b"}"
        code, result = run_cli(["token", f"{b64(deep)}.{b64json({})}.{b64(b'1' * 64)}"])
        self.assertEqual(code, 2)
        code, result = self.jwk('{"keys":' + "[" * 200_000 + "]" * 200_000 + "}")
        self.assertEqual(code, 2)

    def test_non_utf8_jwk_file(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as handle:
            handle.write(b"\xff\xfe{\x00}\x00")
            path = handle.name
        try:
            code, result = run_cli(["jwk", path])
        finally:
            Path(path).unlink()
        self.assertEqual(code, 2)
        self.assertIn("UTF-8", result["error"])

    def test_json_serialization_header_checks(self) -> None:
        flattened = {"payload": "eyJhIjoxfQ", "protected": b64json({"alg": "none"}), "signature": ""}
        _, result = run_cli(["token", json.dumps(flattened)])
        self.assertIn("ALG_NONE", codes(result))
        flattened["protected"] = b64json({"alg": "NONE"})
        _, result = run_cli(["token", json.dumps(flattened)])
        self.assertIn("ALG_CASE_VARIANT", codes(result))
        flattened = {"payload": "eyJhIjoxfQ", "protected": b64json({"alg": "HS256"}), "header": {"crit": ["b64"], "b64": False},
                     "signature": b64(b"1" * 32)}
        _, result = run_cli(["token", json.dumps(flattened)])
        self.assertIn("MUST_BE_PROTECTED", codes(result))

    def test_detached_json_jws(self) -> None:
        detached = {"protected": b64json({"alg": "ES256"}), "signature": b64(b"1" * 64)}
        code, result = run_cli(["token", json.dumps(detached)])
        self.assertEqual(result["kind"], "JWS")
        self.assertIn("DETACHED_PAYLOAD", codes(result))

    def test_thumbprint_kid_with_double_dash_is_not_suspicious(self) -> None:
        _, result = run_cli(["token", make_jws({"alg": "ES256", "kid": "kfPduVQ3T3H6vnewt--ksw"}, GOOD_CLAIMS), "--now", str(NOW)])
        self.assertNotIn("SUSPICIOUS_KID", codes(result))

    def test_rfc7797_unencoded_compact_payload(self) -> None:
        header = b64json({"alg": "HS256", "b64": False, "crit": ["b64"]})
        code, result = run_cli(["token", f"{header}.$02 ok~.{b64(b'1' * 32)}"])
        self.assertEqual(result["payload_text"], "$02 ok~")
        self.assertIn("UNENCODED_PAYLOAD", codes(result))
        self.assertEqual(code, 0)
        code, _ = run_cli(["token", f"{b64json({'alg': 'HS256'})}.$02.{b64(b'1' * 32)}"])
        self.assertEqual(code, 2)  # without "b64": false the BCP format rule applies

    def test_crit_may_list_b64(self) -> None:
        header = b64json({"alg": "HS256", "b64": False, "crit": ["b64"]})
        _, result = run_cli(["token", f"{header}.payload.{b64(b'1' * 32)}"])
        self.assertNotIn("CRIT_INVALID", codes(result))


class Keys(unittest.TestCase):
    def jwk(self, value: Any) -> Tuple[int, Dict[str, Any]]:
        return self.jwk_text(json.dumps(value))

    def jwk_text(self, text: str) -> Tuple[int, Dict[str, Any]]:
        stdin = sys.stdin
        sys.stdin = io.StringIO(text)
        try:
            return run_cli(["jwk", "-"])
        finally:
            sys.stdin = stdin

    def key_codes(self, result: Dict[str, Any], index: int = 0) -> List[str]:
        return [finding["code"] for finding in result["keys"][index]["findings"]]

    def test_rfc7638_thumbprint(self) -> None:
        vector = VECTORS["keys"]["rfc7638-rsa-public"]
        code, result = self.jwk(dict(vector["jwk"], kid="2011-04-29", alg="RS256"))
        self.assertEqual(code, 0)
        self.assertEqual(result["keys"][0]["thumbprint_sha256"], vector["thumbprint"])
        self.assertEqual(result["keys"][0]["bits"], 2048)
        self.assertEqual(result["keys"][0]["thumbprint_uri"], "urn:ietf:params:oauth:jwk-thumbprint:sha-256:" + vector["thumbprint"])

    def test_rfc8037_okp_thumbprint(self) -> None:
        vector = VECTORS["keys"]["rfc8037-a2-ed25519-public"]
        _, result = self.jwk(vector["jwk"])
        self.assertEqual(result["keys"][0]["thumbprint_sha256"], vector["thumbprint"])
        _, private = self.jwk(VECTORS["keys"]["rfc8037-a1-ed25519-private"]["jwk"])
        self.assertEqual(private["keys"][0]["thumbprint_sha256"], vector["thumbprint"])
        self.assertIn("PRIVATE_KEY_MATERIAL", self.key_codes(private))

    def test_public_jwks_is_clean(self) -> None:
        code, result = self.jwk(VECTORS["keys"]["rfc7517-a1-public-jwks"]["jwk"])
        self.assertEqual(code, 0)
        self.assertEqual(result["kind"], "JWK Set")
        self.assertEqual([key["private"] for key in result["keys"]], [False, False])

    def test_private_and_symmetric_material_in_a_set(self) -> None:
        for name in ("rfc7517-a2-private-jwks", "rfc7517-a3-symmetric-jwks"):
            with self.subTest(name=name):
                code, result = self.jwk(VECTORS["keys"][name]["jwk"])
                self.assertEqual(code, 1)
                for index in range(len(result["keys"])):
                    finding = next(f for f in result["keys"][index]["findings"] if f["code"] == "PRIVATE_KEY_MATERIAL")
                    self.assertEqual(finding["level"], "error")
                self.assertNotIn('"d":', json.dumps(result))
                self.assertNotIn('"k":', json.dumps(result))

    def test_private_values_are_never_printed(self) -> None:
        jwk = VECTORS["keys"]["rfc7517-a2-private-jwks"]["jwk"]["keys"][1]
        buffer = io.StringIO()
        stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(jwk))
        try:
            with redirect_stdout(buffer):
                jose_inspect.main(["jwk", "-"])
        finally:
            sys.stdin = stdin
        for member in ("d", "p", "q", "dp", "dq", "qi"):
            self.assertNotIn(jwk[member][:16], buffer.getvalue())

    def test_alg_and_use_conflicts(self) -> None:
        ec = VECTORS["keys"]["rfc7517-a1-public-jwks"]["jwk"]["keys"][0]
        _, result = self.jwk(dict(ec, alg="RS256"))
        self.assertIn("ALG_KTY_MISMATCH", self.key_codes(result))
        _, result = self.jwk(dict(ec, alg="ES384"))
        self.assertIn("ALG_CURVE_MISMATCH", self.key_codes(result))
        _, result = self.jwk(dict(ec, alg="ES256", use="enc"))
        self.assertIn("USE_ALG_CONFLICT", self.key_codes(result))
        _, result = self.jwk(dict(ec, use="sig", key_ops=["encrypt"]))
        self.assertIn("USE_KEY_OPS_CONFLICT", self.key_codes(result))
        _, result = self.jwk(dict(ec, alg="ECDH-ES+A256KW", use="enc"))
        self.assertEqual([c for c in self.key_codes(result) if c.startswith(("ALG_", "USE_"))], [])

    def test_key_sizes(self) -> None:
        _, result = self.jwk({"kty": "oct", "k": b64(b"your-256-bit-secret"), "alg": "HS256"})
        self.assertIn("KEY_TOO_SHORT", self.key_codes(result))
        _, result = self.jwk({"kty": "oct", "k": b64(b"\x00" * 16), "alg": "A256KW"})
        self.assertIn("KEY_LENGTH", self.key_codes(result))
        _, result = self.jwk({"kty": "oct", "k": b64(b"\x00" * 32), "alg": "A256GCM"})
        self.assertNotIn("KEY_LENGTH", self.key_codes(result))
        _, result = self.jwk({"kty": "RSA", "n": b64(b"\xc1" * 128), "e": "AQAB"})
        self.assertIn("RSA_KEY_TOO_SMALL", self.key_codes(result))
        _, result = self.jwk({"kty": "RSA", "n": b64(b"\x00" + b"\xc1" * 256), "e": "AQAB"})
        self.assertIn("NON_MINIMAL_ENCODING", self.key_codes(result))
        _, result = self.jwk({"kty": "EC", "crv": "P-256", "x": b64(b"\x01" * 31), "y": b64(b"\x01" * 32)})
        self.assertIn("COORDINATE_LENGTH", self.key_codes(result))

    def test_set_level_checks(self) -> None:
        ec = VECTORS["keys"]["rfc7517-a1-public-jwks"]["jwk"]["keys"][0]
        _, result = self.jwk({"keys": [ec, dict(ec)]})
        self.assertIn("DUPLICATE_KID", codes(result))
        no_kid = {k: v for k, v in ec.items() if k != "kid"}
        _, result = self.jwk({"keys": [no_kid, ec]})
        self.assertIn("KID_MISSING", codes(result))
        _, result = self.jwk({"keys": []})
        self.assertIn("EMPTY_SET", codes(result))

    def test_unknown_and_invalid(self) -> None:
        _, result = self.jwk({"kty": "XYZ"})
        self.assertIn("UNKNOWN_KTY", self.key_codes(result))
        code, _ = self.jwk({"foo": 1})
        self.assertEqual(code, 2)
        code, _ = self.jwk({"keys": {}})
        self.assertEqual(code, 2)
        code, result = self.jwk_text('{"kty":"oct","kty":"RSA"}')
        self.assertEqual(code, 2)
        self.assertIn("duplicate", result["error"])

    def test_x5c_encoding(self) -> None:
        ec = VECTORS["keys"]["rfc7517-a1-public-jwks"]["jwk"]["keys"][0]
        _, result = self.jwk(dict(ec, x5c=["MIIB-url_safe"]))
        self.assertIn("X5C_ENCODING", self.key_codes(result))

    def test_akp_thumbprint_members(self) -> None:
        key = {"kty": "AKP", "alg": "ML-DSA-44", "pub": b64(b"\x01" * 1312)}
        _, result = self.jwk(key)
        canonical = json.dumps({"alg": "ML-DSA-44", "kty": "AKP", "pub": key["pub"]}, separators=(",", ":"))
        self.assertEqual(result["keys"][0]["thumbprint_sha256"], b64(hashlib.sha256(canonical.encode()).digest()))


if __name__ == "__main__":
    unittest.main(verbosity=1)
