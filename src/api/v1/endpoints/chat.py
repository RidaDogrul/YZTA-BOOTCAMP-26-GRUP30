"""
Chat endpoints — Doğal dil veri analizi soruları.

Tek kaynak akışı (session_id, source_selection boş):
    ChatRequest (session_id + question)
        │
        ▼
    SessionStore → birincil connector
        │
        ▼
    Orchestrator.run(question)
        │
        ▼
    InsightGenerator (LLM) → ChatResponse

Çoklu kaynak akışı (session_id + source_selection dolu):
    ChatRequest (session_id + question + source_selection)
        │
        ▼
    SessionStore → tüm connector'lar + seçilen tablolar
        │
        ▼
    FederatedOrchestrator.run(question)   ← paralel sorgu
        │
        ▼
    InsightGenerator (LLM) → ChatResponse (sources_queried dolu)
"""
from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.federated_orchestrator import FederatedOrchestrator, FederatedResult
from src.agents.llm import get_llm
from src.agents.orchestrator import Orchestrator, OrchestratorResult
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
# Genel yardımcılar
# ---------------------------------------------------------------------------

def _content_to_str(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", item)))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    return str(content).strip()


def _build_cache_key(payload: ChatRequest) -> str:
    # source_selection da cache key'in bir parçası olsun
    sel_str = json.dumps(
        [{"id": s.source_id, "t": sorted(s.tables)} for s in payload.source_selection],
        sort_keys=True,
    )
    return make_cache_key("chat", payload.session_id.strip(), payload.question.strip(), sel_str)


def _df_to_chart_data(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    try:
        # _source_* meta kolonlarını grafik verisinden çıkar
        clean = df.drop(
            columns=[c for c in df.columns if str(c).startswith("_source")],
            errors="ignore",
        )
        return json.loads(clean.head(100).to_json(orient="records"))
    except Exception:
        return []


def _fallback_response(question: str, error_msg: str) -> ChatResponse:
    return ChatResponse(
        status="error",
        summary=(
            "Sorgunuz işlenirken bir sorun oluştu. "
            "Lütfen veri kaynağı bağlantısını kontrol edip tekrar deneyin.\n\n"
            f"Teknik detay: {error_msg}"
        ),
        sql_query=None,
        chart_data=[],
        action_plan=[],
        sources_queried=[],
    )


# ---------------------------------------------------------------------------
# Insight Generator
# ---------------------------------------------------------------------------

def _generate_insight_from_orchestrator(
    question: str,
    orch_result: OrchestratorResult,
    source_alias: str = "Ana Kaynak",
) -> ChatResponse:
    """Tek kaynak OrchestratorResult'tan ChatResponse üretir."""
    llm = get_llm()

    # Veri önizlemesi
    if orch_result.source == "s3" and orch_result.s3_tables:
        merge_kws = ["birleştir", "join", "merge", "hepsini", "tüm", "combine",
                     "beraber", "birlikte", "kombine", "tümünü"]
        wants_merge = any(kw in question.lower() for kw in merge_kws)
        if wants_merge:
            combined = pd.concat(list(orch_result.s3_tables.values()),
                                 ignore_index=True, sort=False)
            data_preview = f"[Tablolar birleştirildi — toplam {len(combined)} satır]\n"
            data_preview += combined.head(20).to_csv(index=False)
        else:
            parts: list[str] = []
            for name, df in orch_result.s3_tables.items():
                parts.append(
                    f"=== TABLO: {name} ({len(df)} satır, "
                    f"sütunlar: {', '.join(str(c) for c in df.columns if c != '_source_file')}) ===\n"
                    + df.drop(columns=["_source_file"], errors="ignore").head(10).to_csv(index=False)
                )
            data_preview = "\n".join(parts)
    elif not orch_result.cleaned_df.empty:
        data_preview = orch_result.cleaned_df.head(20).to_csv(index=False)
    else:
        data_preview = "(Veri yok)"

    source_note = ""
    if orch_result.source == "s3":
        tbl_names = list(orch_result.s3_tables.keys()) if orch_result.s3_tables else []
        source_note = (
            f"\nS3 kaynağı — mevcut tablolar: {', '.join(tbl_names)}\n"
            "Her tabloyu AYRI AYRI analiz et."
        )

    user_content = (
        f"Kullanıcı sorusu: {question}\n\n"
        f"Veri kaynağı: {source_alias}\n"
        f"Yüklenen veriler:\n{orch_result.query}{source_note}\n\n"
        f"Veri temizleme özeti:\n{orch_result.cleaning_summary}\n\n"
        f"Veri önizlemesi:\n{data_preview}"
    )

    parsed = _invoke_insight_llm(llm, user_content)

    chart_data = parsed.get("chart_data") or []
    if not chart_data and not orch_result.cleaned_df.empty:
        chart_data = _df_to_chart_data(orch_result.cleaned_df)

    action_plan = _normalize_action_plan(parsed.get("action_plan"))

    return ChatResponse(
        status="success",
        summary=parsed.get("summary", "Analiz tamamlandı."),
        sql_query=orch_result.query or None,
        chart_data=chart_data,
        action_plan=action_plan,
        sources_queried=[
            {
                "source_id":   "primary",
                "alias":       source_alias,
                "source_type": orch_result.source,
                "success":     True,
                "row_count":   orch_result.row_count,
                "error":       None,
            }
        ],
    )


def _generate_insight_from_federated(
    question: str,
    fed_result: FederatedResult,
) -> ChatResponse:
    """Çoklu kaynak FederatedResult'tan ChatResponse üretir."""
    llm = get_llm()

    # Her kaynaktan gelen verinin kısa önizlemesini hazırla
    previews: list[str] = []
    for pr in fed_result.per_source:
        if not pr.success or pr.df.empty:
            continue
        clean_df = pr.df.drop(
            columns=[c for c in pr.df.columns if str(c).startswith("_source")],
            errors="ignore",
        )
        previews.append(
            f"=== KAYNAK: {pr.alias} ({pr.source_type}) — {pr.row_count} satır ===\n"
            f"Sorgu: {pr.query}\n"
            + clean_df.head(10).to_csv(index=False)
        )

    combined_preview = "\n\n".join(previews) if previews else "(Veri yok)"

    source_summary = ", ".join(
        f"{pr.alias}({'✓' if pr.success else '✗'})" for pr in fed_result.per_source
    )

    user_content = (
        f"Kullanıcı sorusu: {question}\n\n"
        f"Sorgulanan kaynaklar: {source_summary}\n"
        f"Toplam satır: {fed_result.total_rows}\n\n"
        f"Veri temizleme özeti:\n{fed_result.cleaning_summary}\n\n"
        f"Kaynak bazlı veri önizlemesi:\n{combined_preview}"
    )

    if fed_result.failed_sources:
        user_content += (
            f"\n\nNOT: Şu kaynaklar yanıt vermedi: {', '.join(fed_result.failed_sources)}. "
            "Yalnızca başarılı kaynaklardaki veriyi analiz et."
        )

    parsed = _invoke_insight_llm(llm, user_content)

    chart_data = parsed.get("chart_data") or []
    if not chart_data and not fed_result.combined_df.empty:
        chart_data = _df_to_chart_data(fed_result.combined_df)

    action_plan = _normalize_action_plan(parsed.get("action_plan"))

    # Birleşik SQL özeti
    queries = [pr.query for pr in fed_result.per_source if pr.success and pr.query]
    sql_summary = " | ".join(queries) if queries else None

    sources_queried = [
        {
            "source_id":   pr.source_id,
            "alias":       pr.alias,
            "source_type": pr.source_type,
            "success":     pr.success,
            "row_count":   pr.row_count,
            "error":       pr.error,
        }
        for pr in fed_result.per_source
    ]

    status_val = "partial" if fed_result.partial else "success"

    return ChatResponse(
        status=status_val,
        summary=parsed.get("summary", "Analiz tamamlandı."),
        sql_query=sql_summary,
        chart_data=chart_data,
        action_plan=action_plan,
        sources_queried=sources_queried,
    )


def _invoke_insight_llm(llm, user_content: str) -> dict[str, Any]:
    """LLM'i çağırır ve yanıtı parse eder. Hata durumunda fallback dict döner."""
    try:
        response = llm.invoke([
            SystemMessage(content=INSIGHT_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ])
        log_token_usage(response)
        raw = _content_to_str(response.content)
        return _parse_insight_response(raw)
    except Exception as exc:
        logger.warning("Insight LLM hatası", extra={"error": str(exc)})
        return {"summary": user_content[:400], "chart_data": [], "action_plan": []}


def _parse_insight_response(raw: str) -> dict[str, Any]:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", raw, re.DOTALL)
        candidate = brace.group(0) if brace else raw
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {"summary": raw[:800], "chart_data": [], "action_plan": []}


def _normalize_action_plan(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    if isinstance(raw, str):
        return [line.strip("- •").strip() for line in raw.splitlines() if line.strip()]
    return []


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Doğal dilde veri analizi sorusu sor",
    description=(
        "Kullanıcının doğal dilde sorduğu analiz sorusunu alır. "
        "Tek kaynak veya çoklu kaynak (source_selection) modunda çalışır. "
        "Orchestrator (Text-to-SQL / Mongo / S3) + DataScientistAgent + "
        "InsightGenerator (Gemini LLM) pipeline'ından geçirerek "
        "Türkçe özet, grafik ve aksiyon planı döner."
    ),
    response_description="Özet, SQL sorgusu, grafik verisi, aksiyon planı ve kaynak meta bilgisi.",
    responses={
        400: {"model": ErrorResponse, "description": "Eksik session_id veya geçersiz soru"},
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı"},
        500: {"model": ErrorResponse, "description": "Pipeline hatası"},
    },
)
def ask_question(payload: ChatRequest) -> ChatResponse:
    # ── Girdi doğrulama ──────────────────────────────────────────
    if not payload.session_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="session_id boş olamaz.")
    if not payload.question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="question boş olamaz.")

    # ── Cache ────────────────────────────────────────────────────
    cache_key = _build_cache_key(payload)
    cached = query_cache.get(cache_key)
    if isinstance(cached, ChatResponse) and cached.status == "success":
        logger.info("Cache hit", extra={"session_id": payload.session_id})
        return cached
    elif cached is not None:
        query_cache.delete(cache_key)

    # ── Session kontrolü ─────────────────────────────────────────
    session_info = session_store.get_session_info(payload.session_id)
    if session_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Oturum bulunamadı veya süresi doldu.")

    all_sources = session_store.get_all_connectors(payload.session_id)
    if not all_sources:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Oturum bulunamadı veya süresi doldu.")

    logger.info(
        "Chat isteği işleniyor",
        extra={
            "session_id":   payload.session_id,
            "source_count": len(all_sources),
            "multi_source": len(all_sources) > 1 or bool(payload.source_selection),
            "question":     payload.question[:120],
        },
    )

    # ── Kaynak seçimi: hangi connector'lar kullanılacak? ─────────
    # source_selection boşsa → oturumdaki tüm kaynaklar
    sel_map: dict[str, list[str]] = {}
    if payload.source_selection:
        for s in payload.source_selection:
            sel_map[s.source_id] = s.tables

    if sel_map:
        # Sadece seçilen kaynaklara filtrele
        active_sources = [s for s in all_sources if s["source_id"] in sel_map]
        if not active_sources:
            return _fallback_response(
                payload.question,
                "Seçilen source_id'ler bu oturumda bulunamadı.",
            )
    else:
        active_sources = all_sources

    # ── Tek kaynak mı, çoklu mu? ─────────────────────────────────
    use_federated = len(active_sources) > 1

    # ── Tek kaynak yolu ──────────────────────────────────────────
    if not use_federated:
        src        = active_sources[0]
        connector  = src["connector"]
        alias      = src.get("alias", src["source_type"])
        tables     = sel_map.get(src["source_id"], [])

        effective_q = payload.question
        if tables:
            effective_q = (
                f"{payload.question}\n"
                f"[Yalnızca şu tablolar kullanılacak: {', '.join(tables)}]"
            )

        try:
            orch        = Orchestrator(connector=connector)
            orch_result = orch.run(user_question=effective_q, collection=None)
        except Exception as exc:
            logger.error("Orchestrator hatası", extra={"error": str(exc)})
            response = _fallback_response(payload.question, str(exc))
            query_cache.set(cache_key, response, ttl_seconds=60.0)
            return response

        if not orch_result.success:
            logger.warning("Orchestrator başarısız",
                           extra={"stage": orch_result.failed_stage, "error": orch_result.error})
            return _fallback_response(payload.question,
                                      orch_result.error or "Bilinmeyen hata")

        try:
            response = _generate_insight_from_orchestrator(
                payload.question, orch_result, source_alias=alias
            )
        except Exception as exc:
            logger.error("Insight generator hatası", extra={"error": str(exc)})
            response = ChatResponse(
                status="partial",
                summary=orch_result.cleaning_summary or "Analiz tamamlandı.",
                sql_query=orch_result.query or None,
                chart_data=_df_to_chart_data(orch_result.cleaned_df),
                action_plan=[],
                sources_queried=[{
                    "source_id":   src["source_id"],
                    "alias":       alias,
                    "source_type": src["source_type"],
                    "success":     True,
                    "row_count":   orch_result.row_count,
                    "error":       None,
                }],
            )

    # ── Çoklu kaynak yolu ────────────────────────────────────────
    else:
        # FederatedOrchestrator için kaynak listesi hazırla
        fed_sources = []
        for src in active_sources:
            fed_sources.append({
                "connector":   src["connector"],
                "source_type": src["source_type"],
                "alias":       src.get("alias", src["source_type"]),
                "source_id":   src["source_id"],
                "tables":      sel_map.get(src["source_id"], []),
            })

        try:
            fed_orch   = FederatedOrchestrator(sources=fed_sources)
            fed_result = fed_orch.run(user_question=payload.question)
        except Exception as exc:
            logger.error("FederatedOrchestrator hatası", extra={"error": str(exc)})
            response = _fallback_response(payload.question, str(exc))
            query_cache.set(cache_key, response, ttl_seconds=60.0)
            return response

        if not fed_result.success:
            return _fallback_response(
                payload.question,
                fed_result.error or "Hiçbir kaynaktan veri çekilemedi.",
            )

        try:
            response = _generate_insight_from_federated(payload.question, fed_result)
        except Exception as exc:
            logger.error("Federated insight hatası", extra={"error": str(exc)})
            response = ChatResponse(
                status="partial",
                summary=fed_result.cleaning_summary or "Analiz tamamlandı.",
                sql_query=None,
                chart_data=_df_to_chart_data(fed_result.combined_df),
                action_plan=[],
                sources_queried=[
                    {
                        "source_id":   pr.source_id,
                        "alias":       pr.alias,
                        "source_type": pr.source_type,
                        "success":     pr.success,
                        "row_count":   pr.row_count,
                        "error":       pr.error,
                    }
                    for pr in fed_result.per_source
                ],
            )

    # ── Cache ────────────────────────────────────────────────────
    query_cache.set(cache_key, response, ttl_seconds=CHAT_CACHE_TTL_SECONDS)

    logger.info(
        "Chat yanıtı hazır",
        extra={
            "status":        response.status,
            "chart_points":  len(response.chart_data),
            "action_items":  len(response.action_plan),
            "sources":       len(response.sources_queried),
        },
    )
    return response
