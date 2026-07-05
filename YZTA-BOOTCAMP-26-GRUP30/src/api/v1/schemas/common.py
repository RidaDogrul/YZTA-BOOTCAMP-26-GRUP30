"""Tüm endpoint'lerde kullanılan ortak request/response modelleri."""
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Basit mesaj dönen endpoint'ler için standart yanıt."""

    message: str = Field(..., description="İşlem sonucu mesajı", examples=["pong"])

    model_config = {
        "json_schema_extra": {
            "examples": [{"message": "pong"}]
        }
    }


class ErrorResponse(BaseModel):
    """Hata durumlarında dönen standart yanıt formatı."""

    detail: str = Field(
        ...,
        description="Hata açıklaması",
        examples=["Sunucuda beklenmeyen bir hata oluştu."],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"detail": "Geçersiz istek parametresi."}]
        }
    }
