import importlib
import os
import unittest

os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("ENCRYPTION_KEY", "unit-test-encryption-key")
os.environ.setdefault("ENCRYPTION_SALT", "unit-test-salt")

import crypto_utils


class CryptoUtilsTests(unittest.TestCase):
    def setUp(self):
        os.environ["ENCRYPTION_KEY"] = "unit-test-encryption-key"
        os.environ["ENCRYPTION_SALT"] = "unit-test-salt"
        importlib.reload(crypto_utils)

    def test_encrypt_decrypt_round_trip(self):
        plaintext = "secret-token-123"
        ciphertext = crypto_utils.encrypt_value(plaintext)

        self.assertTrue(ciphertext.startswith("enc::"))
        self.assertNotEqual(ciphertext, plaintext)
        self.assertEqual(crypto_utils.decrypt_value(ciphertext), plaintext)

    def test_unencrypted_passthrough(self):
        value = "plain-text"
        self.assertFalse(crypto_utils.is_encrypted(value))
        self.assertEqual(crypto_utils.decrypt_value(value), value)

    def test_encrypt_is_idempotent_for_encrypted_values(self):
        plaintext = "idempotent-test"
        once = crypto_utils.encrypt_value(plaintext)
        twice = crypto_utils.encrypt_value(once)
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
