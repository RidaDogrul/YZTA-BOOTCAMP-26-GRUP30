"""
Health endpoint'leri — Swagger/OpenAPI şablonu.

FS Notları:
- Frontend ilk yüklemede `/health` ve `/api/v1/ping` ile API erişilebilirliğini kontrol edebilir.
- Bu endpoint'ler kimlik doğrulama gerektirmez.
"""
from fastapi import APIRouter

from src.api.v1.schemas.common import MessageResponse

router = APIRouter()


@router.get(
    "/ping",
    response_model=MessageResponse,
    summary="API erişilebilirlik kontrolü",
    description=(
        "Backend API'nin ayakta olduğunu doğrular. "
        "Frontend ve CI/CD health-check senaryolarında kullanılır."
    ),
    response_description="API ayaktaysa `pong` mesajı döner.",
    responses={
        500: {
            "description": "Sunucu hatası",
            "content": {
                "application/json": {
                    "example": {"detail": "Sunucuda beklenmeyen bir hata oluştu."}
                }
            },
        }
    },
)
def ping() -> MessageResponse:
    """Router'ın doğru bağlandığını test eden basit endpoint."""
    return MessageResponse(message="pong")
