"""Rapor listeleme ve detay endpoint'leri için request/response modelleri."""
from typing import Any

from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    """Rapor listesinde gösterilen özet kart."""

    report_id: str = Field(..., description="Rapor benzersiz kimliği", examples=["rpt_001"])
    title: str = Field(..., description="Rapor başlığı", examples=["Tekstil Satış Tahmini"])
    created_at: str = Field(
        ...,
        description="Oluşturulma zamanı (ISO 8601)",
        examples=["2026-07-04T12:00:00+03:00"],
    )
    status: str = Field(..., description="Rapor durumu", examples=["completed"])


class ReportListResponse(BaseModel):
    """Kullanıcının geçmiş rapor listesi."""

    total: int = Field(..., description="Toplam rapor sayısı", examples=[2])
    reports: list[ReportSummary] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": 2,
                    "reports": [
                        {
                            "report_id": "rpt_001",
                            "title": "Tekstil Satış Tahmini",
                            "created_at": "2026-07-04T12:00:00+03:00",
                            "status": "completed",
                        }
                    ],
                }
            ]
        }
    }


class ReportResponse(BaseModel):
    """Tek bir raporun tam içeriği."""

    report_id: str = Field(..., description="Rapor benzersiz kimliği")
    status: str = Field(..., description="Rapor durumu", examples=["success"])
    summary: str = Field(..., description="Türkçe özet")
    chart_data: list[dict[str, Any]] = Field(default_factory=list)
    action_plan: list[str] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_id": "rpt_001",
                    "status": "success",
                    "summary": "Önümüzdeki ay Tekstil kategorisinde %12 ciro kaybı riski tespit edilmiştir.",
                    "chart_data": [
                        {"date": "2026-07-01", "predicted_sales": 12000}
                    ],
                    "action_plan": [
                        "Tekstil kategorisinde acil indirim kampanyası planlayın.",
                    ],
                }
            ]
        }
    }
