"""
Rapor dışa aktarma istek şeması.
Alanlar ChatResponse ile uyumludur; frontend ekrandaki raporu doğrudan
gönderebilir. Raporlar saklanmadığı için içerik istekle birlikte gelir.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ReportExportRequest(BaseModel):
    """İndirilecek raporun içeriği."""

    format: Literal["pdf", "excel"] = Field(
        default="pdf", description="Çıktı biçimi: 'pdf' veya 'excel'."
    )
    title: str = Field(default="Analiz Raporu", description="Rapor başlığı.")
    question: str = Field(default="", description="Kullanıcının sorusu.")
    summary: str = Field(default="", description="Rapor özeti.")
    sql_query: str = Field(default="", description="Çalıştırılan sorgu (şeffaflık için).")
    chart_data: list[dict[str, Any]] = Field(default_factory=list)
    action_plan: list[str] = Field(default_factory=list)
    action_details: list[dict[str, Any]] = Field(
        default_factory=list, description="action / priority / reason alanlı aksiyonlar."
    )
    action_reasoning: str = Field(default="", description="Aksiyon planının gerekçesi.")
    metrics: dict[str, Any] = Field(default_factory=dict)
    language: str = Field(default="tr")