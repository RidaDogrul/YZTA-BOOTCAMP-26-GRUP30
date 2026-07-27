"""Chat (doğal dil sorgu) endpoint'leri için request/response modelleri."""
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceTableSelection(BaseModel):
    """Tek bir kaynak için tablo/koleksiyon seçimi."""

    source_id: str = Field(
        ...,
        description="Seçimin uygulanacağı kaynak kimliği",
        examples=["src_abc123"],
    )
    tables: list[str] = Field(
        default_factory=list,
        description=(
            "Sorgulanacak tablo/koleksiyon adları. "
            "Boş liste → kaynağın tüm şemasını kullan."
        ),
        examples=[["orders", "customers"]],
    )


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
    # Çoklu kaynak desteği — boşsa sadece birincil kaynak kullanılır
    source_selection: list[SourceTableSelection] = Field(
        default_factory=list,
        description=(
            "Hangi kaynakların ve hangi tabloların sorgulanacağını belirtir. "
            "Boş liste → session'daki tüm kaynakları sorgula (tablo kısıtı olmadan). "
            "Belirli kaynaklar için SourceTableSelection listesi gönder."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "sess_abc123",
                    "question": "Son 3 ayda en yüksek ciroyu hangi kategori üretti?",
                },
                {
                    "session_id": "sess_abc123",
                    "question": "Satış ve finans verilerini karşılaştır",
                    "source_selection": [
                        {"source_id": "src_001", "tables": ["orders", "customers"]},
                        {"source_id": "src_002", "tables": ["invoices"]},
                    ],
                },
            ]
        }
    }



class SourceQueryInfo(BaseModel):
    """Standard response metadata for a queried data source."""

    source_id: str = Field(..., description="Queried source id")
    alias: str | None = Field(default=None, description="Human-readable source alias")
    source_type: str = Field(..., description="Source type")
    success: bool = Field(..., description="Whether the source query succeeded")
    row_count: int = Field(default=0, ge=0, description="Number of rows returned by the source")
    error: str | None = Field(default=None, description="Source query error message, if any")


class ChatResponse(BaseModel):
    """Ajan'ın chat sorusuna verdiği yapılandırılmış yanıt."""

    status: Literal["success", "partial", "error"] = Field(
        ...,
        description="Response status",
        examples=["success", "partial", "error"],
    )
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
    # Çoklu kaynak sorgu meta bilgisi
    sources_queried: list[SourceQueryInfo] = Field(
        default_factory=list,
        description=(
            "Her kaynağın sorgu özeti: "
            "[{source_id, alias, source_type, success, row_count, error}, ...]"
        ),
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
                    "sources_queried": [
                        {
                            "source_id": "src_001",
                            "alias": "Satış DB",
                            "source_type": "postgresql",
                            "success": True,
                            "row_count": 240,
                            "error": None,
                        }
                    ],
                }
            ]
        }
    }
