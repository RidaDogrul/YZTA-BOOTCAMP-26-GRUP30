"""Auth endpoint'leri için request/response şemaları."""
from pydantic import BaseModel, EmailStr, Field


# ── Requests ────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Kullanıcı e-posta adresi")
    password: str = Field(..., min_length=6, description="En az 6 karakter şifre")
    full_name: str | None = Field(default=None, description="Ad soyad (opsiyonel)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "kullanici@ornek.com",
                    "password": "gizli123",
                    "full_name": "Ahmet Yılmaz",
                }
            ]
        }
    }


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Kayıtlı e-posta adresi")
    password: str = Field(..., description="Kullanıcı şifresi")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "kullanici@ornek.com", "password": "gizli123"}
            ]
        }
    }


# ── Responses ────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token türü")
    email: str = Field(..., description="Giriş yapan kullanıcının e-postası")
    full_name: str | None = Field(default=None, description="Kullanıcının tam adı")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "email": "kullanici@ornek.com",
                    "full_name": "Ahmet Yılmaz",
                }
            ]
        }
    }


class UserInfoResponse(BaseModel):
    email: str = Field(..., description="Kullanıcı e-postası")
    full_name: str | None = Field(default=None, description="Kullanıcının tam adı")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "kullanici@ornek.com", "full_name": "Ahmet Yılmaz"}
            ]
        }
    }
