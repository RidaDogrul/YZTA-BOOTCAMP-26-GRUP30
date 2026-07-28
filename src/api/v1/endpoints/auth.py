"""
Auth endpoints — Kayıt, giriş ve kullanıcı bilgisi.

POST /auth/register  → Yeni kullanıcı kaydı, JWT döner
POST /auth/login     → E-posta + şifre ile giriş, JWT döner
GET  /auth/me        → Bearer token ile mevcut kullanıcı bilgisi

Kullanıcılar basit bir in-memory dict'te tutulur (MVP).
Production'da bunu bir veritabanı katmanıyla değiştirin.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.v1.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserInfoResponse,
)
from src.api.v1.schemas.common import ErrorResponse
from src.security.jwt_handler import create_access_token, decode_access_token
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# In-memory kullanıcı deposu (MVP)
# Yapı: { email: { "hashed_password": str, "full_name": str | None } }
# ---------------------------------------------------------------------------
_users: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Şifre yardımcıları — passlib yoksa basit hash fallback
# ---------------------------------------------------------------------------
try:
    from passlib.context import CryptContext

    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def _hash_password(plain: str) -> str:
        return _pwd_ctx.hash(plain)

    def _verify_password(plain: str, hashed: str) -> bool:
        return _pwd_ctx.verify(plain, hashed)

except ImportError:  # passlib kurulu değilse SHA-256 fallback
    import hashlib

    logger.warning(
        "passlib kurulu değil; bcrypt yerine SHA-256 kullanılıyor. "
        "Production için 'pip install passlib[bcrypt]' çalıştırın."
    )

    def _hash_password(plain: str) -> str:  # type: ignore[misc]
        return hashlib.sha256(plain.encode()).hexdigest()

    def _verify_password(plain: str, hashed: str) -> bool:  # type: ignore[misc]
        return hashlib.sha256(plain.encode()).hexdigest() == hashed


# ---------------------------------------------------------------------------
# Token bağımlılığı
# ---------------------------------------------------------------------------

def _get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Authorization: Bearer <token> başlığından kullanıcıyı çözer.
    Geçersiz veya eksik token'da 401 fırlatır.
    """
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama başlığı eksik.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(creds.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token geçersiz veya süresi dolmuş.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str | None = payload.get("sub")
    if email is None or email not in _users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sahibi kullanıcı bulunamadı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"email": email, **_users[email]}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kullanıcı kaydı",
    responses={
        409: {"model": ErrorResponse, "description": "E-posta zaten kayıtlı"},
        422: {"model": ErrorResponse, "description": "Geçersiz istek gövdesi"},
    },
)
def register(payload: RegisterRequest) -> TokenResponse:
    """
    Yeni kullanıcı oluşturur ve JWT access token döner.
    Aynı e-posta ile ikinci kayıt denemesinde 409 döner.
    """
    email = payload.email.lower().strip()

    if email in _users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi zaten kayıtlı.",
        )

    _users[email] = {
        "hashed_password": _hash_password(payload.password),
        "full_name": payload.full_name,
    }

    token = create_access_token({"sub": email})
    logger.info("Yeni kullanıcı kaydedildi", extra={"email": email})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        email=email,
        full_name=payload.full_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Kullanıcı girişi",
    responses={
        401: {"model": ErrorResponse, "description": "Hatalı e-posta veya şifre"},
    },
)
def login(payload: LoginRequest) -> TokenResponse:
    """
    E-posta ve şifre ile kimlik doğrular, JWT access token döner.
    Hatalı bilgide 401 döner (hangi alanın yanlış olduğu açıklanmaz).
    """
    email = payload.email.lower().strip()
    user = _users.get(email)

    if user is None or not _verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": email})
    logger.info("Kullanıcı giriş yaptı", extra={"email": email})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        email=email,
        full_name=user.get("full_name"),
    )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="Mevcut kullanıcı bilgisi",
    responses={
        401: {"model": ErrorResponse, "description": "Geçersiz veya eksik token"},
    },
)
def me(current_user: dict = Depends(_get_current_user)) -> UserInfoResponse:
    """
    Geçerli JWT token ile oturum açmış kullanıcının bilgilerini döner.
    """
    return UserInfoResponse(
        email=current_user["email"],
        full_name=current_user.get("full_name"),
    )
