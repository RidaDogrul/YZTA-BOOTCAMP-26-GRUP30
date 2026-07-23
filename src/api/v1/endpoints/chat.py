"""
Chat endpoints — Doğal dil veri analizi soruları.

Akış:
    ChatRequest (session_id + question)
        │
        ▼
    SessionStore → aktif connector
        │
        ▼
    Orchestrator.run(question)          ← Agent 1: Text-to-SQL / Mongo fetch
        │                                 Agent 2: DataScientistAgent (temizleme)
        ▼
    InsightGenerator.run(result)        ← Gemini LLM → summary + chart_data + action_plan
        │
        ▼
    ChatResponse → frontend
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, status
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.agents.orchestrator import Orchestrator
from src.agents.prompts import INSIGHT_GENERATOR_SYSTEM_PROMPT
from src.api.v1.schemas.chat import ChatRequest, ChatResponse
from src.api.v1.schemas.common import ErrorResponse
from src.utils.cache import make_cache_key, query_cache
from src.utils.logger import get_logger
from src.utils.metrics import log_token_usage
from src.utils.session_store import session_store

logger = get_logger(__name__)
router = APIRouter()

CHAT_CACHE_TTL_SECONDS = 300.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_cache_key(payload: ChatRequest) -> str:
    return make_cache_key(
        "chat",
        payload.session_id.strip(),
        payload.question.strip(),
    )


def _df_to_chart_data(df) -> list[dict[str, Any]]:
    """DataFrame'i Chart.js için dict listesine çevirir (max 100 satır)."""
    if df is None or df.empty:
        return []
    try:
        return json.loads(df.head(100).to_json(orient="records"))
    except Exception:
        return []


def _generate_insight(question: str, orch_result) -> ChatResponse:
    """
    OrchestratorResult'tan LLM ile Türkçe özet + aksiyon planı üretir.
    S3 modunda her tablo ayrı preview olarak gönderilir.
    """
    llm = get_llm()

    # ── Veri önizlemesi oluştur ──────────────────────────────────
    if orch_result.source == "s3" and orch_result.s3_tables:
        # Kullanıcı birleştirme istiyor mu?
        merge_keywords = ["birleştir", "join", "merge", "hepsini", "tüm", "combine",
                          "beraber", "birlikte", "kombine", "tümünü"]
        wants_merge = any(kw in question.lower() for kw in merge_keywords)

        if wants_merge:
            # Birleştir ve tek preview
            combined = pd.concat(
                list(orch_result.s3_tables.values()), ignore_index=True, sort=False
            )
            data_preview = f"[Tablolar birleştirildi — toplam {len(combined)} satır]\n"
            data_preview += combined.head(20).to_csv(index=False)
        else:
            # Her tabloyu ayrı ayrı göster
            parts: list[str] = []
            for name, df in orch_result.s3_tables.items():
                parts.append(
                    f"=== TABLO: {name} ({len(df)} satır, "
                    f"sütunlar: {', '.join(str(c) for c in df.columns if c != '_source_file')}) ===\n"
                    + df.drop(columns=["_source_file"], errors="ignore")
                      .head(10).to_csv(index=False)
                )
            data_preview = "\n".join(parts)
    else:
        data_preview = ""
        if not orch_result.cleaned_df.empty:
            data_preview = orch_result.cleaned_df.head(20).to_csv(index=False)

    source_note = ""
    if orch_result.source == "s3":
        table_names = list(orch_result.s3_tables.keys()) if orch_result.s3_tables else []
        source_note = (
            f"\nS3 kaynağı — mevcut tablolar: {', '.join(table_names)}\n"
            "Her tabloyu AYRI AYRI analiz et. "
            "Kullanıcı birleştirme istemedikçe tabloları birbirine karıştırma."
        )

    user_content = (
        f"Kullanıcı sorusu: {question}\n\n"
        f"Yüklenen veriler:\n{orch_result.query}{source_note}\n\n"
        f"Veri temizleme özeti:\n{orch_result.cleaning_summary}\n\n"
        f"Veri önizlemesi:\n{data_preview}"
    )

    messages = [
        SystemMessage(content=INSIGHT_GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    try:
        response = llm.invoke(messages)
        log_token_usage(response)
        raw: str = response.content.strip()
        parsed = _parse_insight_response(raw)
    except Exception as exc:
        logger.warning("Insight LLM hatası, fallback kullanılıyor", extra={"error": str(exc)})
        parsed = {
            "summary": orch_result.cleaning_summary or "Analiz tamamlandı.",
            "chart_data": [],
            "action_plan": [],
        }

    chart_data = parsed.get("chart_data") or []
    # LLM chart_data boş döndürdüyse DataFrame'den üret
    if not chart_data and not orch_result.cleaned_df.empty:
        chart_data = _df_to_chart_data(orch_result.cleaned_df)

    action_plan = parsed.get("action_plan") or []
    if isinstance(action_plan, str):
        # LLM bazen string döndürüyor — satırlara böl
        action_plan = [line.strip("- •").strip() for line in action_plan.splitlines() if line.strip()]

    return ChatResponse(
        status="success",
        summary=parsed.get("summary", "Analiz tamamlandı."),
        sql_query=orch_result.query or None,
        chart_data=chart_data,
        action_plan=action_plan,
    )


def _parse_insight_response(raw: str) -> dict[str, Any]:
    """
    LLM yanıtından JSON'u çıkarır.
    Hem ```json ... ``` bloğu hem de düz JSON desteklenir.
    """
    import re

    # ```json ... ``` veya ``` ... ``` bloğu
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        # İlk { ... } bloğunu bul
        brace = re.search(r"\{.*\}", raw, re.DOTALL)
        candidate = brace.group(0) if brace else raw

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {
            "summary": raw[:800],
            "chart_data": [],
            "action_plan": [],
        }


def _fallback_response(question: str, error_msg: str) -> ChatResponse:
    """Orchestrator veya LLM tamamen çökerse kullanıcıya nazik mesaj döner."""
    return ChatResponse(
        status="error",
        summary=(
            f"Sorgunuz işlenirken bir sorun oluştu. "
            f"Lütfen veri kaynağı bağlantısını kontrol edip tekrar deneyin.\n\n"
            f"Teknik detay: {error_msg}"
        ),
        sql_query=None,
        chart_data=[],
        action_plan=[],
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Doğal dilde veri analizi sorusu sor",
    description=(
        "Kullanıcının doğal dilde sorduğu analiz sorusunu alır. "
        "Orchestrator (Text-to-SQL + veri temizleme) ve Insight Generator "
        "(Gemini LLM) pipeline'ından geçirerek Türkçe özet, grafik ve aksiyon planı döner."
    ),
    response_description="Özet, SQL sorgusu, grafik verisi ve aksiyon planı.",
    responses={
        400: {"model": ErrorResponse, "description": "Eksik session_id veya geçersiz soru"},
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı"},
        500: {"model": ErrorResponse, "description": "Pipeline hatası"},
    },
)
def ask_question(payload: ChatRequest) -> ChatResponse:
    # ── Girdi doğrulama ──────────────────────────────────────────
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

    # ── Cache kontrolü ───────────────────────────────────────────
    cache_key = _build_cache_key(payload)
    cached = query_cache.get(cache_key)
    if isinstance(cached, ChatResponse):
        logger.info("Cache hit", extra={"session_id": payload.session_id})
        return cached

    # ── Session → connector ──────────────────────────────────────
    connector = session_store.get_connector(payload.session_id)
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturum bulunamadı veya süresi doldu.",
        )

    session_info = session_store.get_session_info(payload.session_id)
    source_type = session_info["source_type"] if session_info else "unknown"

    logger.info(
        "Chat isteği işleniyor",
        extra={
            "session_id": payload.session_id,
            "source_type": source_type,
            "question": payload.question[:120],
        },
    )

    # ── Orchestrator ─────────────────────────────────────────────
    try:
        orch = Orchestrator(connector=connector)
        orch_result = orch.run(
            user_question=payload.question,
            collection=None,  # Mongo: auto-detect; SQL/S3: ignored
        )
    except Exception as exc:
        logger.error(
            "Orchestrator başlatma hatası",
            extra={"error": str(exc)},
        )
        response = _fallback_response(payload.question, str(exc))
        query_cache.set(cache_key, response, ttl_seconds=60.0)
        return response

    if not orch_result.success:
        logger.warning(
            "Orchestrator başarısız",
            extra={"stage": orch_result.failed_stage, "error": orch_result.error},
        )
        response = _fallback_response(payload.question, orch_result.error or "Bilinmeyen hata")
        query_cache.set(cache_key, response, ttl_seconds=60.0)
        return response

    # ── Insight Generator (LLM) ───────────────────────────────────
    try:
        response = _generate_insight(payload.question, orch_result)
    except Exception as exc:
        logger.error("Insight generator hatası", extra={"error": str(exc)})
        # LLM hatası → orchestrator verisini doğrudan kullan
        response = ChatResponse(
            status="partial",
            summary=orch_result.cleaning_summary or "Analiz tamamlandı.",
            sql_query=orch_result.query or None,
            chart_data=_df_to_chart_data(orch_result.cleaned_df),
            action_plan=[],
        )

    # ── Cache kaydet ─────────────────────────────────────────────
    query_cache.set(cache_key, response, ttl_seconds=CHAT_CACHE_TTL_SECONDS)

    logger.info(
        "Chat yanıtı hazır",
        extra={
            "status": response.status,
            "chart_points": len(response.chart_data),
            "action_items": len(response.action_plan),
        },
    )
    return response
