"""S3-H2: İçgörü ve tahminlerden somut iş aksiyonları üreten reasoning katmanı."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import json
import math
import re
from typing import Any, Literal, TypeAlias

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.utils.logger import get_logger
from src.utils.metrics import log_token_usage


logger = get_logger(__name__)

Language: TypeAlias = Literal["tr", "en"]
Priority: TypeAlias = Literal["high", "medium", "low"]
RiskLevel: TypeAlias = Literal["high", "medium", "low"]
Trend: TypeAlias = Literal["increase", "decrease", "stable", "unknown"]
PlanSource: TypeAlias = Literal["llm", "fallback"]

MAX_ACTIONS = 4
MAX_CHART_POINTS = 10
_NUMBER_PATTERN = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?")


ACTION_PLANNER_PROMPT_TR = """Sen bir iş aksiyonu planlama ajanısın.

GÖREVİN: Verilen kullanıcı sorusu, analiz özeti ve doğrulanmış metriklerden
uygulanabilir bir aksiyon planı üretmek.

KURALLAR:
- Yalnızca verilen bilgi ve sayıları kullan; yeni sayı, oran veya tarih uydurma.
- Her aksiyon somut, uygulanabilir ve gerekçesi kanıta bağlı olsun.
- Azalış varsa kampanya, stok, maliyet veya müşteri tutundurma önlemlerini değerlendir.
- Artış varsa stok, kapasite ve operasyon hazırlığını değerlendir.
- Tahmin güvenilirliği düşükse kesin karar yerine pilot uygulama ve yakın izleme öner.
- 2 ile 4 arasında aksiyon üret.
- Çıktıya markdown veya açıklama ekleme; yalnızca JSON döndür.

JSON ŞEMASI:
{
  "reasoning": "Kararların kısa genel gerekçesi",
  "actions": [
    {
      "action": "Somut aksiyon",
      "reason": "Bu aksiyonun verilen verilere dayanan gerekçesi",
      "priority": "high | medium | low"
    }
  ]
}
"""


ACTION_PLANNER_PROMPT_EN = """You are a business action-planning agent.

YOUR TASK: Produce an actionable plan from the user question, analysis summary,
and verified metrics provided to you.

RULES:
- Use only the supplied facts and numbers; never invent a number, rate, or date.
- Every action must be concrete, practical, and supported by evidence.
- For a decline, consider campaign, inventory, cost, or retention measures.
- For growth, consider inventory, capacity, and operational readiness.
- If forecast reliability is weak, recommend a limited pilot and close monitoring.
- Produce between 2 and 4 actions.
- Return JSON only; do not add markdown or commentary.

JSON SCHEMA:
{
  "reasoning": "A short overall rationale for the decisions",
  "actions": [
    {
      "action": "Concrete action",
      "reason": "Evidence-based reason for the action",
      "priority": "high | medium | low"
    }
  ]
}
"""


@dataclass(frozen=True)
class ActionItem:
    """Tek bir önceliklendirilmiş ve gerekçelendirilmiş iş aksiyonu."""

    action: str
    reason: str
    priority: Priority = "medium"

    def as_dict(self) -> dict[str, str]:
        return {
            "action": self.action,
            "reason": self.reason,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class ActionPlanResult:
    """Action Planner çıktısı; H1/API entegrasyonu için hazır."""

    actions: list[ActionItem] = field(default_factory=list)
    reasoning: str = ""
    risk_level: RiskLevel = "medium"
    trend: Trend = "unknown"
    source: PlanSource = "llm"
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def action_plan(self) -> list[str]:
        """InsightResult/ChatResponse tarafından beklenen list[str] çıktısı."""
        return [item.action for item in self.actions]

    def as_dict(self) -> dict[str, Any]:
        return {
            "actions": [item.as_dict() for item in self.actions],
            "action_plan": self.action_plan,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "trend": self.trend,
            "source": self.source,
            "error": self.error,
        }


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    return numeric_value if math.isfinite(numeric_value) else None


def _normalize_trend(value: Any) -> Trend:
    normalized = str(value or "").strip().casefold()

    if normalized in {"artış", "artis", "increase", "increasing", "growth", "up"}:
        return "increase"
    if normalized in {"azalış", "azalis", "decrease", "decreasing", "decline", "down"}:
        return "decrease"
    if normalized in {"yatay", "stable", "flat", "steady", "no_change"}:
        return "stable"
    return "unknown"


def _derive_change_from_chart(
    chart_data: Sequence[Mapping[str, Any]],
) -> float | None:
    values = [
        value
        for item in chart_data
        if (value := _to_float(item.get("yhat"))) is not None
    ]
    if len(values) < 2 or abs(values[0]) <= 1e-9:
        return None
    return round((values[-1] - values[0]) / abs(values[0]) * 100, 2)


def _resolve_change_percent(
    metrics: Mapping[str, Any],
    chart_data: Sequence[Mapping[str, Any]],
) -> float | None:
    for key in ("change_percent", "change_pct", "change_percentage"):
        value = _to_float(metrics.get(key))
        if value is not None:
            return value
    return _derive_change_from_chart(chart_data)


def _resolve_trend(
    metrics: Mapping[str, Any],
    change_percent: float | None,
) -> Trend:
    trend = _normalize_trend(metrics.get("trend"))
    if trend != "unknown":
        return trend

    if change_percent is None:
        return "unknown"
    if change_percent > 1:
        return "increase"
    if change_percent < -1:
        return "decrease"
    return "stable"


def _calculate_risk_level(metrics: Mapping[str, Any]) -> RiskLevel:
    """MAPE ve model hata bilgilerine göre karar riskini sınıflandırır."""
    mape = None
    for key in ("mape_percent", "mape", "selected_model_mape"):
        mape = _to_float(metrics.get(key))
        if mape is not None:
            break

    failed_models = metrics.get("failed_models")
    if isinstance(failed_models, Mapping):
        failed_count = len(failed_models)
    elif isinstance(failed_models, Sequence) and not isinstance(
        failed_models,
        (str, bytes),
    ):
        failed_count = len(failed_models)
    else:
        failed_count = 0

    if mape is None:
        return "high" if failed_count >= 2 else "medium"
    if mape > 20 or failed_count >= 2:
        return "high"
    if mape > 10 or failed_count == 1:
        return "medium"
    return "low"


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM çıktısında JSON bulunamadı.")

    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Action Planner çıktısı JSON nesnesi olmalıdır.")
    return parsed


def _normalize_priority(value: Any) -> Priority:
    normalized = str(value or "").strip().casefold()
    aliases: dict[str, Priority] = {
        "high": "high",
        "yüksek": "high",
        "yuksek": "high",
        "medium": "medium",
        "orta": "medium",
        "low": "low",
        "düşük": "low",
        "dusuk": "low",
    }
    return aliases.get(normalized, "medium")


def _normalize_actions(value: Any, overall_reasoning: str) -> list[ActionItem]:
    if not isinstance(value, list):
        return []

    actions: list[ActionItem] = []
    seen: set[str] = set()

    for raw_item in value:
        if isinstance(raw_item, Mapping):
            action = str(raw_item.get("action", "")).strip()
            reason = str(raw_item.get("reason", "")).strip() or overall_reasoning
            priority = _normalize_priority(raw_item.get("priority"))
        elif isinstance(raw_item, str):
            action = raw_item.strip()
            reason = overall_reasoning
            priority = "medium"
        else:
            continue

        deduplication_key = action.casefold()
        if not action or deduplication_key in seen:
            continue

        actions.append(ActionItem(action=action, reason=reason, priority=priority))
        seen.add(deduplication_key)

        if len(actions) == MAX_ACTIONS:
            break

    return actions


def _canonical_number(value: str) -> str | None:
    try:
        number = abs(Decimal(value.replace(",", ".")))
    except InvalidOperation:
        return None
    return format(number.normalize(), "f")


def _numbers_in(value: Any) -> set[str]:
    serialized = json.dumps(value, ensure_ascii=False, default=str)
    return {
        canonical
        for match in _NUMBER_PATTERN.findall(serialized)
        if (canonical := _canonical_number(match)) is not None
    }


def _validate_no_invented_numbers(parsed: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    allowed_numbers = _numbers_in(context)
    produced_numbers = _numbers_in(parsed)
    invented_numbers = produced_numbers - allowed_numbers
    if invented_numbers:
        values = ", ".join(sorted(invented_numbers))
        raise ValueError(f"LLM girdide bulunmayan sayılar üretti: {values}")


def _fallback_actions(
    trend: Trend,
    risk_level: RiskLevel,
    language: Language,
) -> tuple[list[ActionItem], str]:
    if language == "en":
        if trend == "decrease":
            actions = [
                ActionItem(
                    action="Launch a targeted campaign pilot for the products or segments expected to decline.",
                    reason="The verified forecast direction indicates a decline.",
                    priority="high",
                ),
                ActionItem(
                    action="Review inventory and purchasing plans against the expected demand decline.",
                    reason="Aligning supply with weaker demand can limit excess inventory risk.",
                    priority="high",
                ),
            ]
        elif trend == "increase":
            actions = [
                ActionItem(
                    action="Review inventory and operational capacity for the products or segments expected to grow.",
                    reason="The verified forecast direction indicates growth.",
                    priority="high",
                ),
                ActionItem(
                    action="Identify potential supply and service bottlenecks before demand increases.",
                    reason="Operational readiness can reduce missed-sales risk.",
                    priority="medium",
                ),
            ]
        elif trend == "stable":
            actions = [
                ActionItem(
                    action="Maintain the current operating plan while monitoring meaningful deviations.",
                    reason="The verified forecast is broadly stable.",
                    priority="medium",
                ),
                ActionItem(
                    action="Prepare a response threshold for unexpected demand changes.",
                    reason="A predefined response makes monitoring actionable.",
                    priority="low",
                ),
            ]
        else:
            actions = [
                ActionItem(
                    action="Validate the relevant business metric before taking a high-impact action.",
                    reason="The available evidence does not establish a clear trend.",
                    priority="high",
                ),
                ActionItem(
                    action="Collect additional observations and reassess the decision.",
                    reason="More evidence is required for a reliable recommendation.",
                    priority="medium",
                ),
            ]

        if risk_level == "high":
            actions.append(
                ActionItem(
                    action="Test the recommendation with a limited pilot and monitor the result closely.",
                    reason="Forecast reliability indicates elevated decision risk.",
                    priority="high",
                )
            )
        return actions[:MAX_ACTIONS], "A safe rule-based plan was produced from verified trend and risk signals."

    if trend == "decrease":
        actions = [
            ActionItem(
                action="Düşüş beklenen ürün veya segmentler için hedefli bir kampanya pilotu başlatın.",
                reason="Doğrulanmış tahmin eğilimi azalış gösteriyor.",
                priority="high",
            ),
            ActionItem(
                action="Stok ve satın alma planını beklenen talep düşüşüne göre gözden geçirin.",
                reason="Arzı zayıflayan taleple uyumlamak fazla stok riskini azaltabilir.",
                priority="high",
            ),
        ]
    elif trend == "increase":
        actions = [
            ActionItem(
                action="Büyüme beklenen ürün veya segmentler için stok ve operasyon kapasitesini gözden geçirin.",
                reason="Doğrulanmış tahmin eğilimi artış gösteriyor.",
                priority="high",
            ),
            ActionItem(
                action="Talep yükselmeden önce olası tedarik ve hizmet darboğazlarını belirleyin.",
                reason="Operasyon hazırlığı kaçırılan satış riskini azaltabilir.",
                priority="medium",
            ),
        ]
    elif trend == "stable":
        actions = [
            ActionItem(
                action="Anlamlı sapmaları izleyerek mevcut operasyon planını koruyun.",
                reason="Doğrulanmış tahmin genel olarak yatay seyrediyor.",
                priority="medium",
            ),
            ActionItem(
                action="Beklenmeyen talep değişimleri için önceden bir müdahale eşiği belirleyin.",
                reason="Önceden belirlenen tepki planı izlemeyi aksiyona dönüştürür.",
                priority="low",
            ),
        ]
    else:
        actions = [
            ActionItem(
                action="Yüksek etkili bir karar almadan önce ilgili iş metriğini doğrulayın.",
                reason="Mevcut kanıt net bir eğilim göstermiyor.",
                priority="high",
            ),
            ActionItem(
                action="Ek gözlem toplayıp karar değerlendirmesini tekrarlayın.",
                reason="Güvenilir öneri için daha fazla kanıt gerekiyor.",
                priority="medium",
            ),
        ]

    if risk_level == "high":
        actions.append(
            ActionItem(
                action="Öneriyi sınırlı kapsamlı bir pilotla deneyip sonucu yakından izleyin.",
                reason="Tahmin güvenilirliği yüksek karar riskine işaret ediyor.",
                priority="high",
            )
        )

    return actions[:MAX_ACTIONS], "Doğrulanmış eğilim ve risk sinyallerinden güvenli bir kural tabanlı plan üretildi."


class ActionPlanner:
    """Insight Generator çıktılarından nihai aksiyon planı üretir."""

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm or get_llm()

    def run(
        self,
        *,
        question: str,
        summary: str = "",
        metrics: Mapping[str, Any] | None = None,
        chart_data: Sequence[Mapping[str, Any]] | None = None,
        candidate_actions: Sequence[str] | None = None,
        language: Language = "tr",
    ) -> ActionPlanResult:
        """Doğrulanmış içgörüleri LLM reasoning ve güvenli fallback ile aksiyona çevirir."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question boş olamaz.")
        if language not in {"tr", "en"}:
            raise ValueError("language yalnızca 'tr' veya 'en' olabilir.")

        metric_values = dict(metrics or {})
        chart_values = [dict(item) for item in (chart_data or [])]
        candidate_values = [
            str(item).strip()
            for item in (candidate_actions or [])
            if str(item).strip()
        ]

        change_percent = _resolve_change_percent(metric_values, chart_values)
        trend = _resolve_trend(metric_values, change_percent)
        risk_level = _calculate_risk_level(metric_values)

        decision_context: dict[str, Any] = {
            "question": normalized_question,
            "summary": summary.strip(),
            "metrics": metric_values,
            "decision_signals": {
                "trend": trend,
                "change_percent": change_percent,
                "risk_level": risk_level,
            },
            "chart_point_count": len(chart_values),
            "chart_preview": chart_values[:MAX_CHART_POINTS],
            "candidate_actions": candidate_values,
        }

        prompt = ACTION_PLANNER_PROMPT_TR if language == "tr" else ACTION_PLANNER_PROMPT_EN
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=json.dumps(decision_context, ensure_ascii=False, default=str)),
        ]

        logger.info(
            "Action Planner başlıyor",
            extra={
                "language": language,
                "trend": trend,
                "risk_level": risk_level,
                "chart_points": len(chart_values),
                "candidate_actions": len(candidate_values),
            },
        )

        try:
            response = self._llm.invoke(messages)
            log_token_usage(response)
            raw_text = str(getattr(response, "content", response))
            parsed = _extract_json(raw_text)
            _validate_no_invented_numbers(parsed, decision_context)

            reasoning = str(parsed.get("reasoning", "")).strip()
            actions = _normalize_actions(parsed.get("actions"), reasoning)
            if not actions:
                raise ValueError("LLM kullanılabilir bir aksiyon üretmedi.")

            result = ActionPlanResult(
                actions=actions,
                reasoning=reasoning,
                risk_level=risk_level,
                trend=trend,
                source="llm",
            )
            logger.info(
                "Action Planner tamamlandı",
                extra={
                    "action_count": len(result.actions),
                    "risk_level": risk_level,
                    "trend": trend,
                    "source": result.source,
                },
            )
            return result
        except Exception as exc:
            fallback_actions, fallback_reasoning = _fallback_actions(
                trend=trend,
                risk_level=risk_level,
                language=language,
            )
            logger.warning(
                "Action Planner fallback kullandı",
                extra={
                    "error": str(exc),
                    "action_count": len(fallback_actions),
                    "risk_level": risk_level,
                    "trend": trend,
                },
            )
            return ActionPlanResult(
                actions=fallback_actions,
                reasoning=fallback_reasoning,
                risk_level=risk_level,
                trend=trend,
                source="fallback",
                error=str(exc),
            )
