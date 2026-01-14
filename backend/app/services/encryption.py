"""Encryption service for sensitive data management.

Copyright 2025 milbert.ai
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    _instance: EncryptionService | None = None
    _fernet: Fernet | MultiFernet | None = None

    def __new__(cls) -> EncryptionService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the encryption service."""
        keys = self._get_encryption_keys()
        if not keys:
            logger.warning(
                "No encryption key configured. Generating ephemeral key. "
                "Set ENCRYPTION_KEY environment variable for persistent encryption."
            )
            keys = [Fernet.generate_key().decode()]

        # Support key rotation with MultiFernet
        fernet_instances = [Fernet(key.encode()) for key in keys]
        if len(fernet_instances) > 1:
            self._fernet = MultiFernet(fernet_instances)
        else:
            self._fernet = fernet_instances[0]

    def _get_encryption_keys(self) -> list[str]:
        """
        Get encryption keys from settings.

        Supports multiple keys for key rotation.
        Format: "key1,key2,key3" where key1 is the current key.
        """
        if not settings.encryption_key:
            return []

        # Split by comma for key rotation support
        keys = [k.strip() for k in settings.encryption_key.split(",") if k.strip()]
        return keys

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext data.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        if self._fernet is None:
            raise RuntimeError("Encryption not initialized")

        try:
            encrypted = self._fernet.encrypt(plaintext.encode("utf-8"))
            return encrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data") from e

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext data.

        Args:
            ciphertext: The encrypted string to decrypt

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        if self._fernet is None:
            raise RuntimeError("Encryption not initialized")

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted.decode("utf-8")
        except InvalidToken:
            logger.error("Failed to decrypt: Invalid token or key mismatch")
            raise ValueError("Failed to decrypt data: invalid key or corrupted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data") from e

    def encrypt_dict(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt

        Returns:
            Dictionary with specified fields encrypted
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result

    def decrypt_dict(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt

        Returns:
            Dictionary with specified fields decrypted
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(str(result[field]))
                except ValueError:
                    result[field] = None  # Unable to decrypt
        return result

    def hash_for_lookup(self, value: str) -> str:
        """
        Create a hash for lookup purposes (not encryption).

        Useful for creating fingerprints or deduplication.
        """
        if not value:
            return ""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_new_key() -> str:
        """
        Generate a new Fernet encryption key.

        Use this to generate keys for the ENCRYPTION_KEY setting.
        """
        return Fernet.generate_key().decode()

    def rotate_encryption(self, old_ciphertext: str) -> str:
        """
        Re-encrypt data with the current (newest) key.

        Useful when rotating keys - decrypt with any valid key,
        then encrypt with the current key.
        """
        plaintext = self.decrypt(old_ciphertext)
        return self.encrypt(plaintext)


# Singleton instance
encryption_service = EncryptionService()


# Convenience functions
def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data."""
    return encryption_service.encrypt(data)


def decrypt_sensitive_data(data: str) -> str:
    """Decrypt sensitive data."""
    return encryption_service.decrypt(data)


def generate_encryption_key() -> str:
    """Generate a new encryption key for configuration."""
    return EncryptionService.generate_new_key()
