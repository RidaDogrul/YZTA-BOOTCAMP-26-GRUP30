"""
Uygulamanın giriş noktası.
Çalıştırmak için:  python -m uvicorn main:app --reload
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.api.v1.api import api_router
from src.api.v1.openapi import API_DESCRIPTION, OPENAPI_TAGS

# --- Loglama ayarı ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI uygulaması ---
app = FastAPI(
    title="Otonom Data Cleanroom & Tahminleme Ajanı",
    description=API_DESCRIPTION,
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS,
    contact={
        "name": "YZTA Bootcamp Grup 30",
        "url": "https://github.com/RidaDogrul/YZTA-BOOTCAMP-26-GRUP30",
    },
    license_info={
        "name": "Bootcamp Projesi",
    },
)


# --- Global Hata Middleware ---
# Yakalanmayan her hatayı burada tutar; kullanıcıya çirkin bir traceback
# yerine temiz bir JSON döner, hatanın detayı log'a yazılır.
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Beklenmeyen hata oluştu: %s", exc)
            return JSONResponse(
                status_code=500,
                content={"detail": "Sunucuda beklenmeyen bir hata oluştu."},
            )


app.add_middleware(ErrorHandlerMiddleware)

# --- CORS ---
# Frontend farklı bir porttan çalışacağı için API'ye erişebilmesini sağlar.
# Geliştirmede "*"; production'da daraltacağız.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router'ları bağla ---
app.include_router(api_router, prefix="/api/v1")


# --- Sağlık kontrolü ---
@app.get(
    "/health",
    tags=["Health"],
    summary="Sunucu sağlık kontrolü",
    description="Uygulama seviyesinde health-check. Load balancer ve CI/CD için kullanılır.",
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
def health_check():
    return {"status": "ok"}