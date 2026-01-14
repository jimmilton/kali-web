"""Tests for encryption service."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.encryption import (
    EncryptionService,
    encrypt_sensitive_data,
    decrypt_sensitive_data,
    generate_encryption_key,
)


class TestEncryptionService:
    """Test the encryption service."""

    def test_generate_key(self):
        """Test key generation."""
        key = generate_encryption_key()
        assert key is not None
        assert len(key) == 44  # Base64 encoded Fernet key

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt/decrypt works correctly."""
        # Create a fresh instance with a known key
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            plaintext = "sensitive_password_123"
            encrypted = service.encrypt(plaintext)

            # Encrypted should be different from plaintext
            assert encrypted != plaintext
            assert len(encrypted) > 0

            # Decrypt should return original
            decrypted = service.decrypt(encrypted)
            assert decrypted == plaintext

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            result = service.encrypt("")
            assert result == ""

    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            result = service.decrypt("")
            assert result == ""

    def test_decrypt_invalid_data(self):
        """Test decrypting invalid data raises error."""
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            with pytest.raises(ValueError, match="Failed to decrypt"):
                service.decrypt("invalid_encrypted_data")

    def test_encrypt_dict(self):
        """Test encrypting specific fields in a dictionary."""
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            data = {
                "username": "admin",
                "password": "secret123",
                "email": "admin@example.com"
            }

            encrypted = service.encrypt_dict(data, ["password"])

            assert encrypted["username"] == "admin"  # Not encrypted
            assert encrypted["password"] != "secret123"  # Encrypted
            assert encrypted["email"] == "admin@example.com"  # Not encrypted

    def test_decrypt_dict(self):
        """Test decrypting specific fields in a dictionary."""
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            # First encrypt
            data = {"password": "secret123", "username": "admin"}
            encrypted = service.encrypt_dict(data, ["password"])

            # Then decrypt
            decrypted = service.decrypt_dict(encrypted, ["password"])
            assert decrypted["password"] == "secret123"
            assert decrypted["username"] == "admin"

    def test_hash_for_lookup(self):
        """Test hash generation for lookups."""
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            hash1 = service.hash_for_lookup("test_value")
            hash2 = service.hash_for_lookup("test_value")
            hash3 = service.hash_for_lookup("different_value")

            # Same input should produce same hash
            assert hash1 == hash2
            # Different input should produce different hash
            assert hash1 != hash3
            # Hash should be hex string
            assert len(hash1) == 64  # SHA-256 produces 64 hex chars

    def test_generate_secure_token(self):
        """Test secure token generation."""
        key = generate_encryption_key()
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[key]):
            service = object.__new__(EncryptionService)
            service._initialize()

            token1 = service.generate_secure_token()
            token2 = service.generate_secure_token()

            # Tokens should be unique
            assert token1 != token2
            # Default length should produce URL-safe base64
            assert len(token1) > 0

    def test_key_rotation(self):
        """Test encryption with key rotation."""
        old_key = generate_encryption_key()
        new_key = generate_encryption_key()

        # Encrypt with old key
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[old_key]):
            old_service = object.__new__(EncryptionService)
            old_service._initialize()
            encrypted = old_service.encrypt("secret")

        # Decrypt with both keys (new key first for rotation)
        with patch.object(EncryptionService, '_get_encryption_keys', return_value=[new_key, old_key]):
            new_service = object.__new__(EncryptionService)
            new_service._initialize()
            decrypted = new_service.decrypt(encrypted)
            assert decrypted == "secret"

            # Re-encrypt with new key
            rotated = new_service.rotate_encryption(encrypted)
            assert rotated != encrypted
