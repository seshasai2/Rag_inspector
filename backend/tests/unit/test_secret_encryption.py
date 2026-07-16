"""Tests for at-rest secret encryption helpers."""
from app.core.security import decrypt_secret, encrypt_secret


class TestSecretEncryption:
    def test_roundtrip(self):
        plaintext = "JBSWY3DPEHPK3PXP"
        stored = encrypt_secret(plaintext)
        assert stored.startswith("enc:v1:")
        assert plaintext not in stored
        assert decrypt_secret(stored) == plaintext

    def test_legacy_plaintext_passthrough(self):
        legacy = "LEGACYPLAINTEXTSECRET"
        assert decrypt_secret(legacy) == legacy

    def test_encrypted_values_differ(self):
        plaintext = "JBSWY3DPEHPK3PXP"
        a = encrypt_secret(plaintext)
        b = encrypt_secret(plaintext)
        # Fernet includes a timestamp/IV so ciphertexts differ.
        assert a != b
        assert decrypt_secret(a) == decrypt_secret(b) == plaintext
