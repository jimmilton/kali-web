"""Security utilities for authentication and encryption."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
    additional_claims: dict | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, datetime]:
    """
    Create a JWT refresh token.

    Returns:
        Tuple of (token, token_hash, expiration_datetime)
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    # Generate a random token ID for additional security
    token_id = secrets.token_urlsafe(32)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": token_id,
    }

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    # Hash the token for storage
    token_hash = hashlib.sha256(encoded_jwt.encode()).hexdigest()

    return encoded_jwt, token_hash, expire


def verify_token(token: str, token_type: str = "access") -> dict | None:
    """
    Verify a JWT token and return the payload.

    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Verify token type
        if payload.get("type") != token_type:
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None

        return payload

    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data using Fernet."""
    from app.services.encryption import encryption_service
    return encryption_service.encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data using Fernet."""
    from app.services.encryption import encryption_service
    return encryption_service.decrypt(encrypted_data)


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (api_key, api_key_hash)
    """
    api_key = f"kali_{secrets.token_urlsafe(32)}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return api_key, api_key_hash


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """Verify an API key against its hash."""
    return hashlib.sha256(api_key.encode()).hexdigest() == api_key_hash


def generate_mfa_secret() -> str:
    """Generate a secret for MFA (TOTP)."""
    import pyotp
    return pyotp.random_base32()


def verify_mfa_code(secret: str, code: str) -> bool:
    """Verify a MFA code against a secret."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


def generate_mfa_qr_uri(secret: str, email: str) -> str:
    """Generate a URI for MFA QR code."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="Kali Tools")


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate backup codes for MFA recovery."""
    return [secrets.token_hex(4).upper() for _ in range(count)]
