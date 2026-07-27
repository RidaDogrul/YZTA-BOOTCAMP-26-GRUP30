"""
Rapor endpoint'leri — Swagger/OpenAPI şablonu.

FS Notları:
- Dashboard ana sayfası `/reports` ile geçmiş raporları listeler.
- `/reports/{report_id}` ile detay sayfası açılır.
- Rapor içeriği chat yanıtıyla aynı JSON yapısını kullanır (tutarlı frontend modeli).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi import Depends
from src.api.middleware.auth import CurrentUser, get_current_user

from src.agents.insight_generator import InsightGeneratorAgent
from src.agents.orchestrator import Orchestrator
from src.api.v1.schemas.chat import ChatResponse
from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.reports import (
    GenerateReportRequest,
    ReportListResponse,
    ReportResponse,
    ReportSummary,
)
from src.utils.logger import get_logger
from src.utils.session_store import session_store

logger = get_logger(__name__)
router = APIRouter()

# In-memory report storage (production'da database kullanılmalı)
# Format: {report_id: {"report_id": str, "user_id": str, "created_at": str, "content": dict, "share_with_emails": list[str], "make_public": bool, "public_link": str}}
report_store: dict[str, dict[str, Any]] = {}


@router.get(
    "",
    response_model=ReportListResponse,
    summary="Rapor listesini getir",
    description=(
        "Kullanıcının daha önce oluşturduğu tüm raporların özet listesini döner. "
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
    """Geçmiş raporların özet listesini döner."""
    # TODO(Sprint-3): Veritabanı / depolama entegrasyonu
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


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Rapor detayını getir",
    description=(
        "Belirtilen rapor kimliğine ait tam içeriği döner: özet, grafik datası ve aksiyon planı. "
        "Frontend rapor detay sayfası bu endpoint'i kullanır."
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
    """Tek bir raporun detayını döner."""
    if report_id == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapor bulunamadı.",
        )

    # TODO(Sprint-3): report_id ile depodan okuma
    return ReportResponse(
        report_id=report_id,
        status="success",
        summary="Şablon rapor — gerçek veri Sprint 3'te eklenecek.",
        chart_data=[{"date": "2026-07-01", "predicted_sales": 12000}],
        action_plan=["Örnek aksiyon maddesi."],
    )


@router.post(
    "/generate",
    response_model=ChatResponse,
    summary="Insight Generator ile rapor oluştur",
    description=(
        "Verilen oturum ve soru için InsightGeneratorAgent kullanarak "
        "detaylı rapor (özet, grafik verisi, aksiyon planı) oluşturur."
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
) -> ChatResponse:
    """InsightGeneratorAgent kullanarak rapor oluşturur."""
    # ── Girdi doğrulama ──────────────────────────────────────────
    if not payload.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id boş olamaz."
        )

    # ── Session kontrolü ─────────────────────────────────────────
    session_info = session_store.get_session_info(payload.session_id)
    if session_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturum bulunamadı veya süresi doldu."
        )

    all_sources = session_store.get_all_connectors(payload.session_id)
    if not all_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturum bulunamadı veya süresi doldu."
        )

    logger.info(
        "Rapor oluşturma isteği",
        extra={
            "session_id": payload.session_id,
            "chat_history_count": len(payload.chat_history),
            "language": payload.language,
        },
    )

    # ── Sohbet geçmişinden bağlam oluştur ─────────────────────────
    # Son kullanıcı sorularını ve yanıtlarını birleştir
    context_questions = []
    for msg in payload.chat_history:
        if msg.get("role") == "user":
            content = msg.get("content") or msg.get("text", "")
            if content and content.strip():
                context_questions.append(content.strip())
    
    # Eğer sohbet geçmişi yoksa ve question da yoksa hata döndür
    if not context_questions and not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rapor oluşturmak için sohbet geçmişi veya soru gerekli."
        )
    
    # Bağlam sorusu oluştur - son soruyu kullan veya verilen soruyu
    if payload.question.strip():
        analysis_question = payload.question.strip()
    elif context_questions:
        analysis_question = context_questions[-1]  # Son soru
    else:
        analysis_question = "Verilerin genel analizi ve özeti"
    
    # Analysis question boş olmamalı
    if not analysis_question or not analysis_question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analiz sorusu boş olamaz."
        )

    # ── Dil tespiti: soru dilinden otomatik ─────────────────────
    # payload.language "tr" ise frontend'den açıkça gönderilmiş demektir;
    # ama asıl belirleyici her zaman kullanıcının sorusudur.
    from src.agents.insight_generator import _detect_language as _detect_lang
    detected_language = _detect_lang(analysis_question)
    # Frontend'den "tr" gönderilmiş ama soru İngilizce ise detected'ı kullan
    effective_language = detected_language  # sorudan tespit ettiğimiz dil kazanır

    # ── Birincil kaynağı al ─────────────────────────────────────
    src = all_sources[0]
    connector = src["connector"]
    alias = src.get("alias", src["source_type"])

    # ── Orchestrator ile veriyi al ───────────────────────────────
    try:
        logger.info("Orchestrator başlatılıyor", extra={"analysis_question": analysis_question, "source_type": src["source_type"]})
        orch = Orchestrator(connector=connector)
        orch_result = orch.run(user_question=analysis_question, collection=None)
    except ValueError as exc:
        # SQL executor'dan gelen özel hatalar (boş şema, güvenlik vb.)
        logger.error("Orchestrator ValueError", extra={"error": str(exc), "analysis_question": analysis_question})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Veri işleme hatası: {str(exc)}"
        )
    except Exception as exc:
        logger.error("Orchestrator hatası", extra={"error": str(exc), "analysis_question": analysis_question})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Veri işleme hatası: {str(exc)}"
        )

    if not orch_result.success:
        logger.warning(
            "Orchestrator başarısız",
            extra={"stage": orch_result.failed_stage, "error": orch_result.error}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=orch_result.error or "Bilinmeyen hata"
        )

    # ── InsightGeneratorAgent ile rapor oluştur ───────────────────
    try:
        insight_agent = InsightGeneratorAgent(language=effective_language)
        
        # Sohbet geçmişi bağlamını ekle
        enhanced_question = analysis_question
        if context_questions:
            enhanced_question = f"Sohbet geçmişi bağlamında: {' | '.join(context_questions[-3:])}\n\nAna soru: {analysis_question}"
        
        insight_result = insight_agent.run(
            question=enhanced_question,
            cleaned_df=orch_result.cleaned_df,
            forecast_result=None,
            cleaning_report=None,
            language=effective_language,  # ← tespit edilmiş dili kullan
        )

        if not insight_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=insight_result.error or "Rapor oluşturma hatası"
            )

        # ── ChatResponse formatında döndür ─────────────────────────
        response = ChatResponse(
            status="success",
            summary=insight_result.summary,
            sql_query=orch_result.query or None,
            chart_data=insight_result.chart_data,
            action_plan=insight_result.action_plan,
            sources_queried=[
                {
                    "source_id": src["source_id"],
                    "alias": alias,
                    "source_type": src["source_type"],
                    "success": True,
                    "row_count": orch_result.row_count,
                    "error": None,
                }
            ],
        )
        
        # ── Raporu kaydet ve paylaşım ayarlarını uygula ───────────────
        report_id = f"rpt_{uuid.uuid4().hex[:8]}"
        public_link = None
        
        if payload.make_public:
            # Herkese açık link oluştur
            public_link = f"/api/v1/reports/public/{report_id}"
        
        report_data = {
            "report_id": report_id,
            "user_id": session_info.get("user_id", "anonymous"),
            "created_at": datetime.now().isoformat(),
            "content": response.model_dump(),
            "share_with_emails": payload.share_with_emails,
            "make_public": payload.make_public,
            "public_link": public_link,
            "title": analysis_question[:50] + "..." if len(analysis_question) > 50 else analysis_question,
        }
        
        report_store[report_id] = report_data
        logger.info(f"Report saved: {report_id}, public_link: {public_link}, make_public: {payload.make_public}")
        
        # Email gönderme simülasyonu (production'da gerçek email servisi kullanılmalı)
        if payload.share_with_emails:
            logger.info(
                "Rapor email gönderilecek",
                extra={
                    "report_id": report_id,
                    "emails": payload.share_with_emails,
                }
            )
            # TODO: Gerçek email gönderme servisi entegrasyonu
        
        # Response'a rapor ID ve paylaşım linki ekle
        response.report_id = report_id
        response.public_link = public_link
        
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("InsightGenerator hatası", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rapor oluşturma hatası: {str(exc)}"
        )


@router.get(
    "/public/{report_id}",
    response_model=ChatResponse,
    summary="Herkese açık raporu getir",
    description=(
        "Rapor ID'si ile herkese açık raporu getirir. "
        "Rapor make_public=true olarak oluşturulmuş olmalıdır."
    ),
    response_description="Rapor içeriği.",
    responses={
        404: {"model": ErrorResponse, "description": "Rapor bulunamadı veya herkese açık değil"},
    },
)
def get_public_report(report_id: str) -> ChatResponse:
    """Herkese açık raporu getirir."""
    logger.info(f"Public report requested: {report_id}")
    logger.info(f"Available reports: {list(report_store.keys())}")
    
    if report_id not in report_store:
        logger.warning(f"Report not found: {report_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapor bulunamadı."
        )
    
    report_data = report_store[report_id]
    
    if not report_data.get("make_public", False):
        logger.warning(f"Report not public: {report_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu rapor herkese açık değil."
        )
    
    logger.info(f"Returning public report: {report_id}")
    return ChatResponse(**report_data["content"])
