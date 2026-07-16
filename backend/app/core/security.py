import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update(
        {
            "exp": expire,
            "type": "access",
            "jti": secrets.token_urlsafe(16),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_mfa_challenge_token(user_id: str, expires_minutes: int = 5) -> str:
    """Short-lived token proving password auth; not usable as an access token."""
    to_encode = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        "type": "mfa_challenge",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def generate_api_key() -> tuple[str, str]:
    """Returns (raw_key, hashed_key). Store only hash."""
    raw = "ri-" + secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def get_key_prefix(raw_key: str) -> str:
    return raw_key[:10]


_FERNET_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    # Derive a stable Fernet key from SECRET_KEY (32 url-safe base64-encoded bytes).
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a sensitive string for at-rest storage (e.g. MFA TOTP secrets)."""
    if not plaintext:
        raise ValueError("plaintext secret required")
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{_FERNET_PREFIX}{token}"


def decrypt_secret(stored: str) -> str:
    """Decrypt a value produced by ``encrypt_secret``.

    Legacy plaintext values (no ``enc:v1:`` prefix) are returned as-is so
    existing MFA factors keep working until re-enrolled.
    """
    if not stored:
        raise ValueError("stored secret required")
    if not stored.startswith(_FERNET_PREFIX):
        return stored
    token = stored[len(_FERNET_PREFIX) :]
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
