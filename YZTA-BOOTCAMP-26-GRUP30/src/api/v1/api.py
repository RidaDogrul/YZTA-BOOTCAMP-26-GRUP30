"""
Tüm /api/v1 endpoint'lerinin toplandığı merkezi router.

Yeni endpoint eklerken:
1. src/api/v1/endpoints/ altında route dosyası oluştur
2. src/api/v1/schemas/ altına request/response modellerini ekle
3. Bu dosyada router'ı include_router ile bağla
"""
from fastapi import APIRouter

from src.api.v1.endpoints import chat, connect_db, health, reports

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(
    connect_db.router,
    prefix="/connect-db",
    tags=["Connect DB"],
)
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
