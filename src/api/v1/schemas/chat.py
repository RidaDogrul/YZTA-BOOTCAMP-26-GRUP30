"""Chat (doğal dil sorgu) endpoint'leri için request/response modelleri."""
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Kullanıcının ajan'a gönderdiği doğal dil sorusu."""

    session_id: str = Field(
        ...,
        description="Aktif veri kaynağı oturum kimliği (connect_db'den alınır)",
        examples=["sess_abc123"],
    )
    question: str = Field(
        ...,
        description="Kullanıcının doğal dilde sorduğu analiz/tahmin sorusu",
        min_length=3,
        examples=["Önümüzdeki ay en çok satış yapılacak kategori hangisi?"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "sess_abc123",
                    "question": "Son 3 ayda en yüksek ciroyu hangi kategori üretti?",
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Ajan'ın chat sorusuna verdiği yapılandırılmış yanıt."""

    status: str = Field(..., description="İşlem durumu", examples=["success"])
    summary: str = Field(
        ...,
        description="Türkçe özet cevap",
        examples=["Tekstil kategorisi son 3 ayın lideri olarak öne çıkıyor."],
    )
    sql_query: str | None = Field(
        default=None,
        description="Arka planda üretilen SQL sorgusu (debug/şeffaflık için)",
    )
    chart_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Frontend grafik bileşenleri için veri",
    )
    action_plan: list[str] = Field(
        default_factory=list,
        description="Önerilen aksiyon maddeleri",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "summary": "Önümüzdeki ay Tekstil kategorisinde %12 ciro kaybı riski tespit edilmiştir.",
                    "sql_query": "SELECT category, SUM(revenue) FROM sales GROUP BY category",
                    "chart_data": [
                        {"date": "2026-07-01", "predicted_sales": 12000}
                    ],
                    "action_plan": [
                        "Tekstil kategorisinde acil indirim kampanyası planlayın.",
                        "Tedarik siparişlerini %10 kısın.",
                    ],
                }
            ]
        }
    }
