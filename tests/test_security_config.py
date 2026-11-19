"""Valida a configuração de segurança sem ler segredos ou bancos reais."""

from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch

from security.config import load_security_settings


class SecurityConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = Path(self.directory.name) / ".env"
        self.key = secrets.token_urlsafe(48)
        self.environment = patch.dict("os.environ", {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_missing_empty_short_and_example_keys_are_rejected_without_exposure(self):
        for value in (None, "", "curta", "SUBSTITUA_POR_UMA_CHAVE_ALEATORIA"):
            with self.subTest(value=value):
                self.env.write_text("" if value is None else f"JWT_SECRET_KEY={value}\n", encoding="utf8")
                with self.assertRaises(ValueError) as error:
                    load_security_settings(self.env)
                if value:
                    self.assertNotIn(value, str(error.exception))

    def test_file_and_defaults_and_hidden_secret(self):
        self.env.write_text(f"JWT_SECRET_KEY={self.key}\nJWT_ALGORITHM=none\n", encoding="utf8")
        settings = load_security_settings(self.env)
        self.assertEqual(settings.secret_key.get_secret_value(), self.key)
        self.assertEqual(settings.algorithm, "HS256")
        self.assertEqual(settings.access_token_expire_minutes, 30)
        self.assertNotIn(self.key, repr(settings))
        self.assertNotIn(self.key, str(settings.secret_key))

    def test_process_environment_has_priority(self):
        self.env.write_text("JWT_SECRET_KEY=curta\nACCESS_TOKEN_EXPIRE_MINUTES=10\n", encoding="utf8")
        with patch.dict("os.environ", {"JWT_SECRET_KEY": self.key, "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}):
            settings = load_security_settings(self.env)
        self.assertEqual(settings.secret_key.get_secret_value(), self.key)
        self.assertEqual(settings.access_token_expire_minutes, 15)

    def test_empty_process_key_does_not_fall_back_to_file(self):
        self.env.write_text(f"JWT_SECRET_KEY={self.key}\n", encoding="utf8")
        with patch.dict("os.environ", {"JWT_SECRET_KEY": ""}), self.assertRaises(ValueError):
            load_security_settings(self.env)

    def test_invalid_expiration_is_rejected(self):
        for value in ("", "0", "-1", "1.5", "texto"):
            with self.subTest(value=value):
                self.env.write_text(f"JWT_SECRET_KEY={self.key}\nACCESS_TOKEN_EXPIRE_MINUTES={value}\n", encoding="utf8")
                with self.assertRaisesRegex(ValueError, "inteiro positivo"):
                    load_security_settings(self.env)
