"""
Insight Generator Agent (Agent 3) — Task S3-H1
------------------------------------------------
Temizlenmiş veriyi ve tahmin sonuçlarını alıp kullanıcıya sunulacak
Türkçe/İngilizce rapora çevirir.

İŞ BÖLÜMÜ (tasarım kararı):
  - LLM YALNIZCA metin üretir: summary + aday aksiyonlar.
  - chart_data ve tüm sayısal metrikler KOD tarafında gerçek veriden
    hesaplanır. Böylece LLM'in sayı uydurma riski ortadan kalkar.
  - Nihai aksiyon planı, S3-H2'deki ActionPlanner'a devredilir; Agent 3'ün
    ürettiği aksiyonlar oraya "aday" (candidate_actions) olarak gider.

Çıktı, chat.py'daki ChatResponse şemasına doğrudan oturur:
  {status, summary, sql_query, chart_data, action_plan}
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.agents.prompts import (
    INSIGHT_GENERATOR_PROMPT_EN,
    INSIGHT_GENERATOR_PROMPT_TR,
)
from src.agents.tools.action_planner import ActionPlanner
from src.security.anonymizer import PIIAnonymizer
from src.utils.logger import get_logger

# ForecastResult'ı yalnızca TİP DENETİMİ için import ediyoruz. Çalışma anında
# import edilmez; böylece Agent 3, forecaster.py'nin ağır ML bağımlılıklarını
# (lightgbm, prophet, statsmodels) yüklemek zorunda kalmaz. Agent 3 sadece
# nesnenin alanlarını kullanır (duck-typing).
if TYPE_CHECKING:
    from src.ml_models.forecaster import ForecastResult

logger = get_logger(__name__)

Language = Literal["tr", "en"]

MAX_SAMPLE_ROWS = 20      # LLM'e gönderilecek örnek satır sayısı (token tasarrufu)
MAX_CHART_ROWS = 200      # chart_data'ya konacak maksimum satır

# PIIAnonymizer singleton — pahalı init (spaCy model yükleme)
try:
    _pii_anonymizer = PIIAnonymizer()
    _PII_AVAILABLE = True
except Exception as _pii_err:
    logger.warning(
        "PIIAnonymizer yüklenemedi — PII maskeleme devre dışı",
        extra={"error": str(_pii_err)}
    )
    _pii_anonymizer = None  # type: ignore[assignment]
    _PII_AVAILABLE = False


# ---------------------------------------------------------------------------
# Sonuç veri sınıfı
# ---------------------------------------------------------------------------
@dataclass
class InsightResult:
    """Agent 3'ün çıktısı — API'ye ve frontend'e hazır."""

    summary: str = ""
    action_plan: list[str] = field(default_factory=list)
    chart_data: list[dict[str, Any]] = field(default_factory=list)
    language: str = "tr"
    metrics: dict[str, Any] = field(default_factory=dict)   # kodun hesapladığı metrikler
    action_reasoning: str = ""                              # planın genel gerekçesi
    action_details: list[dict[str, Any]] = field(default_factory=list)  # action/reason/priority
    action_plan_source: str = "insight_llm"                 # "llm" | "fallback" | "insight_llm"
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_chat_payload(self, sql_query: str = "") -> dict[str, Any]:
        """chat.py'daki ChatResponse şemasına uygun sözlük döndürür."""
        return {
            "status": "success" if self.success else "error",
            "summary": self.summary,
            "sql_query": sql_query,
            "chart_data": self.chart_data,
            "action_plan": self.action_plan,
        }


# ---------------------------------------------------------------------------
# Yardımcılar — LLM'e verilecek bağlamı hazırlar (hepsi gerçek veriden)
# ---------------------------------------------------------------------------
def _apply_pii_mask_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame'i PIIAnonymizer ile maskeler.
    Anonymizer yoksa veya hata çıkarsa orijinali döner (güvenli fallback).
    """
    if not _PII_AVAILABLE or _pii_anonymizer is None:
        return df
    try:
        return _pii_anonymizer.anonymize_dataframe(df)
    except Exception as exc:
        logger.warning("PII maskeleme hatası (DataFrame)", extra={"error": str(exc)})
        return df


def _apply_pii_mask_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Dict listesindeki (chart_data gibi) PII değerlerini maskeler.
    """
    if not _PII_AVAILABLE or _pii_anonymizer is None or not rows:
        return rows
    try:
        return [_pii_anonymizer.anonymize_dict(row) for row in rows]
    except Exception as exc:
        logger.warning("PII maskeleme hatası (rows)", extra={"error": str(exc)})
        return rows

def _json_safe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame'i JSON'a güvenli kayıt listesine çevirir (tarih/NaN dahil)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _build_data_context(df: pd.DataFrame) -> dict[str, Any]:
    """
    Veri hakkında LLM'e verilecek özet bağlam.
    LLM'e gönderilecek örnek satırlar PII maskeli; istatistikler ham veriden.
    """
    context: dict[str, Any] = {
        "row_count": int(len(df)),
        "columns": [str(c) for c in df.columns],
    }

    # Sayısal istatistikler ham veriden hesaplanır — maskeleme yapmıyoruz
    numeric = df.select_dtypes("number")
    if not numeric.empty:
        context["numeric_summary"] = json.loads(numeric.describe().round(2).to_json())

    # Örnek satırlar LLM'e gitmeden önce PII maskele
    sample_df = _apply_pii_mask_df(df.head(MAX_SAMPLE_ROWS))
    context["sample_rows"] = _json_safe(sample_df)

    return context


def _build_forecast_context(result: ForecastResult) -> dict[str, Any]:
    """Tahmin sonucundan LLM'e verilecek özet + yön/değişim hesabı."""
    forecast = result.forecast
    first_value = float(forecast["yhat"].iloc[0])
    last_value = float(forecast["yhat"].iloc[-1])

    # Değişim yüzdesi — sıfıra bölmeye karşı korumalı.
    if abs(first_value) > 1e-9:
        change_pct = round((last_value - first_value) / abs(first_value) * 100, 2)
    else:
        change_pct = 0.0

    if change_pct > 1:
        trend = "artış"
    elif change_pct < -1:
        trend = "azalış"
    else:
        trend = "yatay"

    return {
        "selected_model": result.selected_model,
        "mape_percent": round(result.model_scores.get(result.selected_model, 0.0), 2),
        "all_model_scores": {k: round(v, 2) for k, v in result.model_scores.items()},
        "failed_models": list(result.failed_models.keys()),
        "horizon_days": int(len(forecast)),
        "start_date": str(pd.Timestamp(forecast["ds"].iloc[0]).date()),
        "end_date": str(pd.Timestamp(forecast["ds"].iloc[-1]).date()),
        "first_value": round(first_value, 2),
        "last_value": round(last_value, 2),
        "total": round(float(forecast["yhat"].sum()), 2),
        "mean": round(float(forecast["yhat"].mean()), 2),
        "change_percent": change_pct,
        "trend": trend,
        "has_prediction_intervals": "yhat_lower_80" in forecast.columns,
    }


def _build_chart_data(
    df: pd.DataFrame,
    forecast_result: ForecastResult | None,
) -> list[dict[str, Any]]:
    """
    Grafik verisini GERÇEK veriden üretir (LLM'den değil).
    Tahmin varsa tahmin serisini, yoksa temizlenmiş veriyi döndürür.
    Çıktı PII maskeli olur.
    """
    if forecast_result is not None:
        forecast = forecast_result.forecast.head(MAX_CHART_ROWS)
        rows: list[dict[str, Any]] = []
        for _, row in forecast.iterrows():
            item: dict[str, Any] = {
                "ds": str(pd.Timestamp(row["ds"]).date()),
                "yhat": round(float(row["yhat"]), 2),
                "type": "forecast",
            }
            # Güven aralıkları varsa grafiğe bant olarak eklenebilsin.
            for level in (80, 95):
                lower_col, upper_col = f"yhat_lower_{level}", f"yhat_upper_{level}"
                if lower_col in forecast.columns:
                    item[lower_col] = round(float(row[lower_col]), 2)
                    item[upper_col] = round(float(row[upper_col]), 2)
            rows.append(item)
        # Tahmin verisi PII içermez genelde ama yine de maskeleyelim
        return _apply_pii_mask_rows(rows)

    # Tahmin yoksa: temizlenmiş verinin kendisi grafik verisidir — PII maskele
    chart_df = _apply_pii_mask_df(df.head(MAX_CHART_ROWS))
    return _json_safe(chart_df)


def _extract_text_content(content) -> str:
    """
    LLM response.content farklı formatlarda gelebilir:
      - str                          → doğrudan döndür
      - list[str]                    → birleştir
      - list[dict]  (Gemini format)  → "text" alanlarını birleştir
      - dict with 'text' field       → text alanını döndür
      - str representation of dict   → parse and extract text
    """
    if isinstance(content, str):
        content = content.strip()
        # Eğer string bir dict representation ise (örn: "{'type': 'text', 'text': '...'}")
        if content.startswith("{") and content.endswith("}"):
            try:
                # Try to parse as dict using ast.literal_eval for safety
                import ast
                parsed = ast.literal_eval(content)
                if isinstance(parsed, dict) and "text" in parsed:
                    return str(parsed["text"]).strip()
            except:
                # If parsing fails, the string might be incomplete or malformed
                # Try to extract text field using a more robust method
                # Look for 'text': and extract everything after it until the end of the string
                # or until we hit a closing brace that's not part of the JSON
                text_key_pos = content.find("'text'")
                if text_key_pos == -1:
                    text_key_pos = content.find('"text"')
                
                if text_key_pos != -1:
                    # Find the colon after 'text'
                    colon_pos = content.find(":", text_key_pos)
                    if colon_pos != -1:
                        # Find the opening quote after the colon
                        quote_start = content.find("'", colon_pos)
                        if quote_start == -1:
                            quote_start = content.find('"', colon_pos)
                        
                        if quote_start != -1:
                            # Extract everything from after the quote to the end
                            # Then remove trailing whitespace and the closing brace/quote
                            text = content[quote_start + 1:].rstrip()
                            # Remove trailing '}' or '"' if present
                            if text.endswith("}"):
                                text = text[:-1].rstrip()
                            if text.endswith("'") or text.endswith('"'):
                                text = text[:-1].rstrip()
                            # Unescape
                            text = text.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'").replace("\\\\", "\\")
                            return text.strip()
        return content
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
    if isinstance(content, dict):
        # Tek dict ise text alanını al
        return str(content.get("text", content)).strip()
    return str(content).strip()


def _extract_json(text: str) -> dict[str, Any]:
    """
    LLM çıktısından JSON'u güvenli biçimde ayıklar.
    LLM bazen ```json ... ``` bloğu veya öncesinde/sonrasında metin ekler;
    bu fonksiyon onları temizler.
    Gemini formatında (list[dict] with type/text) gelen yanıtları da handle eder.
    """
    if not text or not text.strip():
        raise ValueError("LLM çıktısı boş.")
    
    # Önce markdown code block'ları temizle
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    
    # JSON bloğunu bul
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM çıktısında JSON bulunamadı.")
    
    json_str = cleaned[start : end + 1]
    
    # Eğer JSON single quotes kullanıyorsa, double quotes'a çevir
    # Ama dikkatli ol - string içindeki single quotes'ı değiştirme
    if "'" in json_str and '"' not in json_str[:50]:  # Başlangıçta double quote yoksa, single quotes kullanılıyordur
        # Basit yaklaşım: tüm single quotes'ı double quotes'a çevir
        # Bu her zaman doğru değil ama çoğu durumda işe yarar
        json_str = json_str.replace("'", '"')
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        # JSON parse hatası - daha detaylı hata mesajı
        # Eğer hata "Expecting property name" ise, bu muhtemelen single quotes kullanılmış demektir
        # Single quotes'ı double quotes'a çevirip tekrar dene
        if "Expecting property name" in str(exc):
            try:
                # Single quotes'ı double quotes'a çevir (basit yaklaşım)
                json_str_fixed = json_str.replace("'", '"')
                return json.loads(json_str_fixed)
            except:
                pass
        raise ValueError(f"JSON parse hatası: {exc}. Ham metin: {json_str[:200]}")


def _detect_language(text: str) -> str:
    """
    Metnin dilini tespit eder (geliştirilmiş Türkçe/İngilizce ayrımı).
    
    Öncelik sırası:
    1. Türkçe özel karakterler (ç, ğ, ı, ö, ş, ü) → kesin Türkçe
    2. Yaygın Türkçe kelimeler → muhtemel Türkçe
    3. Yaygın İngilizce kelimeler → muhtemel İngilizce
    4. Varsayılan → İngilizce (çoğu teknik terim İngilizce)
    """
    if not text or not text.strip():
        return "en"  # Boş input için İngilizce varsayılan
    
    text_lower = text.lower()
    
    # 1. Türkçe özel karakter kontrolü (kesin belirleyici)
    turkish_chars = set("çğıöşü")
    if any(char in turkish_chars for char in text_lower):
        return "tr"
    
    # 2. Yaygın Türkçe kelimeler (güncellenmiş liste)
    turkish_words = {
        # Bağlaçlar
        "ve", "veya", "ama", "fakat", "ancak", "çünkü", "için", "ile", "gibi",
        # Soru kelimeleri
        "ne", "nedir", "nasıl", "hangi", "kim", "nerede", "ne zaman", "kaç", "niye", "niçin",
        # Fiiller
        "göster", "analiz", "yap", "bul", "getir", "çıkar", "hesapla", "sırala", "listele",
        "karşılaştır", "özetle", "açıkla", "tahmin", "ver", "çek",
        # İsimler
        "toplam", "ortalama", "maksimum", "minimum", "sayı", "miktar", "değer",
        "tablo", "veri", "rapor", "sonuç", "kategori", "ürün", "müşteri", "satış",
        # Sıfatlar
        "en", "çok", "az", "yüksek", "düşük", "son", "ilk", "önümüzdeki", "geçen",
        # Zaman
        "ay", "gün", "hafta", "yıl", "bugün", "dün", "yarın",
    }
    
    # 3. Yaygın İngilizce kelimeler
    english_words = {
        # Verbs
        "show", "analyze", "find", "get", "calculate", "sort", "list", "compare",
        "summarize", "explain", "predict", "give", "fetch", "display",
        # Nouns
        "total", "average", "maximum", "minimum", "number", "amount", "value",
        "table", "data", "report", "result", "category", "product", "customer", "sales",
        # Adjectives
        "highest", "lowest", "last", "first", "next", "previous", "top", "bottom",
        # Time
        "day", "week", "month", "year", "today", "yesterday", "tomorrow",
        # Questions
        "what", "how", "which", "who", "where", "when", "why",
    }
    
    # Kelimeleri ayıkla
    words = re.findall(r"\b\w+\b", text_lower)
    if not words:
        return "en"
    
    turkish_count = sum(1 for word in words if word in turkish_words)
    english_count = sum(1 for word in words if word in english_words)
    
    # Eğer Türkçe kelime oranı %15'ten fazlaysa Türkçe
    if words and turkish_count / len(words) > 0.15:
        return "tr"
    
    # Eğer İngilizce kelime oranı %15'ten fazlaysa İngilizce
    if words and english_count / len(words) > 0.15:
        return "en"
    
    # Türkçe ve İngilizce kelime sayısını karşılaştır
    if turkish_count > english_count:
        return "tr"
    elif english_count > turkish_count:
        return "en"
    
    # Varsayılan: İngilizce (teknik terimler için)
    return "en"


def _normalize_action_plan(value: Any) -> list[str]:
    """
    action_plan'ı her zaman list[str] yapar.
    (ChatResponse şeması liste bekliyor; LLM bazen tek string döndürebilir.)
    """
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


# ---------------------------------------------------------------------------
# Agent 3
# ---------------------------------------------------------------------------
class InsightGeneratorAgent:
    """
    Agent 3: analiz + tahmin sonuçlarını Türkçe/İngilizce rapora çevirir.

    Args:
        llm: LangChain sohbet modeli (verilmezse get_llm() kullanılır).
        language: Varsayılan rapor dili ("tr" | "en").
        action_planner: S3-H2 ActionPlanner örneği. Verilmezse aynı LLM ile
            otomatik kurulur.
        use_action_planner: False ise plan üretimi ActionPlanner'a devredilmez;
            Agent 3'ün kendi LLM önerileri kullanılır (test/çevrimdışı senaryo).
    """

    def __init__(
        self,
        llm: Any = None,
        language: Language = "tr",
        action_planner: ActionPlanner | None = None,
        use_action_planner: bool = True,
    ) -> None:
        self._llm = llm or get_llm()
        self._default_language = language
        # Aynı LLM örneğini paylaşıyoruz; gereksiz ikinci model kurulumu olmasın.
        self._action_planner: ActionPlanner | None = (
            (action_planner or ActionPlanner(llm=self._llm)) if use_action_planner else None
        )

    def run(
        self,
        question: str,
        cleaned_df: pd.DataFrame,
        forecast_result: ForecastResult | None = None,
        cleaning_report: dict[str, Any] | None = None,
        language: Language | None = None,
    ) -> InsightResult:
        """
        Rapor üretir.

        Args:
            question: Kullanıcının orijinal sorusu.
            cleaned_df: Agent 2'nin temizlediği veri.
            forecast_result: Varsa tahmin motorunun sonucu.
            cleaning_report: Varsa Agent 2'nin yapısal temizleme raporu.
            language: Rapor dili; None ise sorudan otomatik tespit edilir.
        """
        # Dil tespiti: açıkça belirtilmişse kullan, değilse sorudan tespit et
        if language is not None:
            lang = language
        else:
            detected = _detect_language(question)
            lang = detected or self._default_language

        # --- Boş veri: LLM'e gitmeye gerek yok ---
        if cleaned_df is None or cleaned_df.empty:
            message = (
                "Sorgu sonucunda veri bulunamadı."
                if lang == "tr"
                else "The query returned no data."
            )
            return InsightResult(summary=message, language=lang)

        # --- 1) Bağlamı GERÇEK veriden hazırla ---
        context: dict[str, Any] = {
            "user_question": question,
            "data": _build_data_context(cleaned_df),
        }
        if forecast_result is not None:
            context["forecast"] = _build_forecast_context(forecast_result)
        if cleaning_report:
            context["data_cleaning"] = cleaning_report

        # --- 2) chart_data'yı KOD hesaplar (LLM değil) ---
        chart_data = _build_chart_data(cleaned_df, forecast_result)
        metrics: dict[str, Any] = context.get("forecast", {})

        # --- 3) LLM'den özet + aday aksiyonlar iste ---
        system_prompt = (
            INSIGHT_GENERATOR_PROMPT_TR if lang == "tr" else INSIGHT_GENERATOR_PROMPT_EN
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(context, ensure_ascii=False, default=str)),
        ]

        logger.info(
            "Agent 3 (Insight Generator) başlıyor",
            extra={"language": lang, "rows": len(cleaned_df),
                   "has_forecast": forecast_result is not None},
        )

        raw_text = ""
        try:
            response = self._llm.invoke(messages)
            raw_text = _extract_text_content(response.content)
            logger.info("LLM yanıt alındı", extra={"raw_text_length": len(raw_text), "raw_text_preview": raw_text[:200]})
            parsed = _extract_json(raw_text)
        except ValueError as exc:
            # JSON parse edilemedi: ham metni özet olarak kullan, akışı kesme.
            logger.error("Agent 3 JSON ayrıştırma hatası", extra={"error": str(exc)})
            return InsightResult(
                summary=raw_text.strip(),
                chart_data=chart_data,
                language=lang,
                metrics=metrics,
                error=f"Rapor JSON olarak ayrıştırılamadı: {exc}",
            )
        except Exception as exc:  
            logger.error("Agent 3 başarısız", extra={"error": str(exc)})
            return InsightResult(
                chart_data=chart_data,
                language=lang,
                metrics=metrics,
                error=f"İçgörü üretme hatası: {exc}",
            )

        summary = str(parsed.get("summary", "")).strip()
        candidate_actions = _normalize_action_plan(parsed.get("action_plan"))

        # --- 4) Nihai aksiyon planını S3-H2 ActionPlanner'a devret ---
        result = InsightResult(
            summary=summary,
            action_plan=candidate_actions,
            chart_data=chart_data,
            language=lang,
            metrics=metrics,
        )

        if self._action_planner is not None:
            plan = self._action_planner.run(
                question=question,
                summary=summary,
                metrics=metrics,
                chart_data=chart_data,
                candidate_actions=candidate_actions,   # Agent 3'ün önerileri aday olarak gider
                language=lang,
            )
            if plan.actions:
                result.action_plan = plan.action_plan
                result.action_reasoning = plan.reasoning
                result.action_details = [item.as_dict() for item in plan.actions]
                result.action_plan_source = plan.source
            # Not: planner fallback'e düşse bile kullanılabilir bir plan döner,
            # bu yüzden InsightResult.error'a dokunmuyoruz; kaynak bilgisi
            # action_plan_source alanında görünür.

        logger.info(
            "Agent 3 tamamlandı",
            extra={"summary_length": len(result.summary),
                   "action_items": len(result.action_plan),
                   "action_source": result.action_plan_source,
                   "chart_points": len(result.chart_data)},
        )
        return result


# ---------------------------------------------------------------------------
# Hızlı test — python -m src.agents.insight_generator
# Gerçek DB gerekmez; sahte veri + sahte tahmin sonucu kullanılır.
# (GOOGLE_API_KEY gereklidir.)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    # Sahte temizlenmiş veri
    df = pd.DataFrame(
        {
            "ds": pd.date_range("2026-06-01", periods=10, freq="D"),
            "amount": [1200, 1350, 1180, 1420, 1500, 1610, 1580, 1700, 1750, 1820],
        }
    )

    # Sahte tahmin sonucu: ForecastResult ile AYNI alanlara sahip hafif bir
    # nesne. Böylece test için ML kütüphanelerini kurmak gerekmez.
    from types import SimpleNamespace

    future = pd.date_range("2026-06-11", periods=7, freq="D")
    forecast_result = SimpleNamespace(
        selected_model="prophet",
        model_scores={"prophet": 6.4, "arima": 9.1, "lightgbm": 7.8},
        failed_models={},
        forecast=pd.DataFrame(
            {"ds": future, "yhat": [1850, 1900, 1930, 1975, 2010, 2060, 2100]}
        ),
    )

    cleaning_report = {
        "initial_shape": [10, 2],
        "final_shape": [10, 2],
        "nulls_filled": {"amount": 1},
        "outliers_handled": {"amount": 1},
    }

    agent = InsightGeneratorAgent()

    for lang in ("tr", "en"):
        print(f"\n{'=' * 20} DİL: {lang} {'=' * 20}")
        result = agent.run(
            question="Önümüzdeki hafta satışlar ne olur?",
            cleaned_df=df,
            forecast_result=forecast_result,  # type: ignore[arg-type]  # test için sahte nesne
            cleaning_report=cleaning_report,
            language=lang,  # type: ignore[arg-type]
        )
        print("Başarılı:", result.success)
        print("\n--- Özet ---")
        print(result.summary)
        print(f"\n--- Aksiyon planı (kaynak: {result.action_plan_source}) ---")
        for item in result.action_details or [{"action": a} for a in result.action_plan]:
            priority = item.get("priority", "")
            prefix = f"[{priority}] " if priority else ""
            print(f" - {prefix}{item['action']}")
        if result.action_reasoning:
            label = "Gerekçe" if lang == "tr" else "Reasoning"
            print(f"\n{label}: {result.action_reasoning}")
        print(f"\n--- Grafik verisi ({len(result.chart_data)} nokta, ilk 3) ---")
        print(result.chart_data[:3])
        print("\n--- API payload (ChatResponse formatı) ---")
        print(json.dumps(result.to_chat_payload(sql_query="SELECT ..."),
                         ensure_ascii=False)[:300], "...")