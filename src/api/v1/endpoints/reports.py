"""
Rapor endpoint'leri.

- GET  /reports                 → Dashboard için rapor özet listesi (şablon).
- GET  /reports/{report_id}     → Rapor detayı (şablon).
- POST /reports/generate        → InsightGeneratorAgent ile gerçek rapor üretir.
- POST /reports/export          → Raporu PDF/Excel olarak indirir.

Not: Raporlar sunucuda kalıcı saklanmaz (Elif'in kararı). /generate anlık
rapor üretir; indirme için içerik istekle birlikte gelir.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.agents.insight_generator import InsightGeneratorAgent
from src.agents.orchestrator import Orchestrator
from src.api.middleware.auth import CurrentUser, get_current_user
from src.api.v1.schemas.chat import ChatResponse
from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.export import ReportExportRequest
from src.api.v1.schemas.reports import (
    GenerateReportRequest,
    ReportListResponse,
    ReportResponse,
    ReportSummary,
)
from src.services.report_exporter import export_report as build_export
from src.utils.logger import get_logger
from src.utils.session_store import session_store

import base64
import os
from typing import Optional

import resend
from pydantic import BaseModel
from typing import Any, Optional
logger = get_logger(__name__)

router = APIRouter()

class EmailReportRequest(BaseModel):
    to: str
    subject: str
    html: Optional[str] = None
    pdf_base64: Optional[str] = None
    filename: str = "rapor.pdf"


@router.post(
    "/email",
    summary="Raporu e-posta ile gönder",
    description="Raporu (PDF ek dosyasıyla) belirtilen adrese Resend üzerinden gönderir.",
)
def email_report(payload: EmailReportRequest) -> dict:
    """Raporu tek bir alıcıya PDF ekiyle mail atar."""
    resend.api_key = os.getenv("RESEND_API_KEY")
    if not resend.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RESEND_API_KEY tanımlı değil (.env kontrol edin).",
        )

    params: dict[str, Any] = {
        "from": os.getenv("MAIL_FROM", "onboarding@resend.dev"),
        "to": [payload.to],
        "subject": payload.subject or "Analiz Raporu",
        "html": payload.html or "<p>Analiz raporunuz ektedir.</p>",
    }

    # PDF varsa ek dosya olarak koy
    if payload.pdf_base64:
        b64 = payload.pdf_base64.split(",")[-1]  # "data:...base64," önekini at
        raw = base64.b64decode(b64)
        params["attachments"] = [
            {"filename": payload.filename or "rapor.pdf", "content": list(raw)}
        ]

    try:
        result = resend.Emails.send(params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mail gönderilemedi: {exc}",
        )

    return {"status": "sent", "id": result.get("id") if isinstance(result, dict) else None}

# ---------------------------------------------------------------------------
# GET /reports — Dashboard rapor listesi (şablon)
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=ReportListResponse,
    summary="Rapor listesini getir",
    description=(
        "Kullanıcının oluşturduğu raporların özet listesini döner. "
        "Dashboard ana sayfasındaki rapor kartları bu endpoint'i kullanır."
    ),
    response_description="Rapor özet kartları listesi.",
    responses={
        500: {"model": ErrorResponse, "description": "Rapor listesi alınamadı"},
    },
)
def list_reports(
    current_user: CurrentUser = Depends(get_current_user),
) -> ReportListResponse:
    """Rapor özet listesini döner (şablon; raporlar sunucuda saklanmaz)."""
    return ReportListResponse(
        total=1,
        reports=[
            ReportSummary(
                report_id="rpt_template_001",
                title="Örnek Satış Tahmini",
                created_at="2026-07-04T12:00:00+03:00",
                status="completed",
            )
        ],
    )


# ---------------------------------------------------------------------------
# GET /reports/{report_id} — Rapor detayı (şablon)
# ---------------------------------------------------------------------------
@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Rapor detayını getir",
    description=(
        "Belirtilen rapor kimliğine ait tam içeriği döner: özet, grafik verisi "
        "ve aksiyon planı."
    ),
    response_description="Raporun tam içeriği.",
    responses={
        404: {"model": ErrorResponse, "description": "Rapor bulunamadı"},
        500: {"model": ErrorResponse, "description": "Rapor okunamadı"},
    },
)
def get_report(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> ReportResponse:
    """Tek bir raporun detayını döner (şablon)."""
    if report_id == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapor bulunamadı.",
        )
    return ReportResponse(
        report_id=report_id,
        status="success",
        summary="Şablon rapor — gerçek veri /generate ile üretilir.",
        chart_data=[{"date": "2026-07-01", "predicted_sales": 12000}],
        action_plan=["Örnek aksiyon maddesi."],
    )


# ---------------------------------------------------------------------------
# POST /reports/generate — Gerçek rapor üretimi (Orchestrator + Agent 3)
# ---------------------------------------------------------------------------
@router.post(
    "/generate",
    response_model=ChatResponse,
    summary="Insight Generator ile rapor oluştur",
    description=(
        "Verilen oturum ve soru için Orchestrator + InsightGeneratorAgent "
        "kullanarak rapor (özet, grafik verisi, aksiyon planı) üretir."
    ),
    response_description="ChatResponse formatında rapor içeriği.",
    responses={
        400: {"model": ErrorResponse, "description": "Eksik session_id veya geçersiz soru"},
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı"},
        500: {"model": ErrorResponse, "description": "Rapor oluşturma hatası"},
    },
)
def generate_report(
    payload: GenerateReportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    """Orchestrator ve InsightGeneratorAgent ile gerçek rapor üretir."""
    if not payload.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id boş olamaz.",
        )
    if not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question boş olamaz.",
        )

    # Oturum kontrolü
    session_info = session_store.get_session_info(payload.session_id)
    if session_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturum bulunamadı veya süresi doldu.",
        )

    connectors = session_store.get_all_connectors(payload.session_id)
    if not connectors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturuma bağlı veri kaynağı yok.",
        )

    logger.info(
        "Rapor oluşturma isteği",
        extra={"session_id": payload.session_id, "language": payload.language},
    )

    # Birincil kaynak üzerinden çalış
    primary = connectors[0]
    connector = primary["connector"]

    # Orchestrator: veri çek + temizle
    try:
        orch = Orchestrator(connector=connector)
        orch_result = orch.run(payload.question)
    except Exception as exc:  # noqa: BLE001
        logger.error("Orchestrator hatası", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Veri işleme hatası: {exc}",
        ) from exc

    if not orch_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=orch_result.error or "Bilinmeyen hata",
        )

    # Insight Generator: rapor üret
    try:
        insight_agent = InsightGeneratorAgent(language=payload.language)
        insight_result = insight_agent.run(
            question=payload.question,
            cleaned_df=orch_result.cleaned_df,
            forecast_result=None,
            cleaning_report=orch_result.cleaning_report,
            language=payload.language,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("InsightGenerator hatası", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rapor oluşturma hatası: {exc}",
        ) from exc

    if not insight_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=insight_result.error or "Rapor oluşturma hatası",
        )

    return ChatResponse(
        status="success",
        summary=insight_result.summary,
        sql_query=orch_result.query or "",
        chart_data=insight_result.chart_data,
        action_plan=insight_result.action_plan,
    )


# ---------------------------------------------------------------------------
# POST /reports/export — PDF / Excel indirme
# ---------------------------------------------------------------------------
@router.post(
    "/export",
    summary="Raporu PDF veya Excel olarak indir",
    description=(
        "Gönderilen rapor içeriğini PDF ya da Excel dosyasına çevirir ve indirir. "
        "Raporlar sunucuda saklanmadığı için içerik istek gövdesinde gönderilir."
    ),
    response_description="İndirilebilir dosya (PDF veya XLSX).",
    responses={
        200: {
            "content": {
                "application/pdf": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
            "description": "Rapor dosyası",
        },
        400: {"model": ErrorResponse, "description": "Geçersiz format"},
        500: {"model": ErrorResponse, "description": "Rapor oluşturulamadı"},
    },
)
def export_report_endpoint(
    payload: ReportExportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Rapor içeriğini istenen dosya biçiminde döndürür."""
    try:
        content, filename, media_type = build_export(
            payload.model_dump(), payload.format
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rapor dosyası oluşturulamadı.",
        ) from exc

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )