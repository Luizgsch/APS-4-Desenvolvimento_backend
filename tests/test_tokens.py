"""JWT adversariais assinados somente com chaves descartáveis de teste."""

import base64
import json
import secrets
import time
import unittest
from unittest.mock import patch

import jwt
from pydantic import SecretStr

from security.config import SecuritySettings
from security.tokens import TokenInvalidoError, criar_token, validar_token


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.key = secrets.token_urlsafe(48)
        self.settings = SecuritySettings(SecretStr(self.key), access_token_expire_minutes=15)
        config = patch("security.tokens.load_security_settings", return_value=self.settings)
        config.start()
        self.addCleanup(config.stop)
        self.now = int(time.time())
        self.claims = {"sub": "1", "iat": self.now, "exp": self.now + 900}

    def token(self, claims=None, key=None, algorithm="HS256"):
        return jwt.encode(self.claims if claims is None else claims, key or self.key, algorithm=algorithm)

    def test_valid_token_has_minimal_claims_and_configured_expiration(self):
        token = criar_token(42)
        claims = jwt.decode(token, self.key, algorithms=["HS256"])
        self.assertEqual(set(claims), {"sub", "iat", "exp"})
        self.assertEqual(claims["sub"], "42")
        self.assertEqual(claims["exp"] - claims["iat"], 900)
        self.assertEqual(validar_token(token), 42)

    def test_expired_and_future_issued_tokens_are_rejected(self):
        for claims in (self.claims | {"iat": self.now - 60, "exp": self.now - 1},
                       self.claims | {"iat": self.now + 60}):
            with self.assertRaises(TokenInvalidoError):
                validar_token(self.token(claims))

    def test_wrong_signature_and_tampered_payload_are_rejected(self):
        with self.assertRaises(TokenInvalidoError):
            validar_token(self.token(key=secrets.token_urlsafe(48)))
        parts = self.token().split(".")
        parts[1] = base64.urlsafe_b64encode(json.dumps(self.claims | {"sub": "2"}).encode()).rstrip(b"=").decode()
        with self.assertRaises(TokenInvalidoError):
            validar_token(".".join(parts))

    def test_wrong_algorithm_and_unsigned_tokens_are_rejected(self):
        for token in (self.token(algorithm="HS384"), jwt.encode(self.claims, "", algorithm="none")):
            with self.assertRaises(TokenInvalidoError):
                validar_token(token)

    def test_missing_required_claims_and_invalid_subjects_are_rejected(self):
        for field in ("sub", "exp", "iat"):
            with self.assertRaises(TokenInvalidoError):
                validar_token(self.token({k: v for k, v in self.claims.items() if k != field}))
        for subject in (None, "", "0", "-1", "01", "1.0", "abc", "١", 1, True, "9223372036854775808"):
            with self.subTest(subject=subject), self.assertRaises(TokenInvalidoError):
                validar_token(self.token(self.claims | {"sub": subject}))

    def test_invalid_date_types_and_chronology_are_rejected(self):
        for change in ({"exp": str(self.now + 900)}, {"exp": self.now + 900.5},
                       {"exp": None}, {"iat": str(self.now)}, {"iat": True},
                       {"iat": self.now - 1, "exp": self.now - 2}, {"exp": float("inf")}):
            with self.subTest(change=change), self.assertRaises(TokenInvalidoError):
                validar_token(self.token(self.claims | change))

    def test_malformed_token_has_no_sensitive_exception_message(self):
        for token in ("", "TOKEN_INTERNO", "a.b.c"):
            with self.assertRaises(TokenInvalidoError) as error:
                validar_token(token)
            self.assertNotIn(token or "TOKEN_INTERNO", str(error.exception))

    def test_generation_rejects_invalid_identity(self):
        for subject in (0, -1, True, "1", 9223372036854775808):
            with self.assertRaises(ValueError):
                criar_token(subject)
