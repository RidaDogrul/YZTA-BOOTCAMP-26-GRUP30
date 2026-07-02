"""
Tüm /api/v1 endpoint'lerinin toplandığı merkezi router.
İleride her yeni özellik (chat, connect_db, reports...) buraya eklenecek.
"""
from fastapi import APIRouter

api_router = APIRouter()


# Sprint 2'de eklenecek örnek (şimdilik yorum):
# from src.api.v1.endpoints import chat
# api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])


@api_router.get("/ping", tags=["Health"])
def ping():
    """Router'ın doğru bağlandığını test eden basit endpoint."""
    return {"message": "pong"}