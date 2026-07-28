"""
JWT token üretme ve doğrulama yardımcı modülü.

Kullanım:
    token = create_access_token({"sub": "kullanici@ornek.com"})
    payload = decode_access_token(token)  # geçersizse None döner
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.utils.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Verilen payload ile JWT access token üretir.

    :param data:          Token içine gömülecek claims (örn. {"sub": "email"})
    :param expires_delta: Özel süre; None ise config'den alınır
    :return:              Imzalı JWT string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(timezone.utc)

    encoded = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Token'ı doğrular ve payload'u döner.

    :param token: JWT string
    :return:      Geçerliyse payload dict, değilse None
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except ExpiredSignatureError:
        logger.warning("JWT süresi dolmuş")
        return None
    except InvalidTokenError as exc:
        logger.warning("Geçersiz JWT token", extra={"error": str(exc)})
        return None
