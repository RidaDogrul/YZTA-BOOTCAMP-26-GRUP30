"""
Text-to-SQL Katmanı (Görev S2-H2)
-----------------------------------
Kullanıcının doğal dildeki sorusunu ve veritabanı şemasını alır;
LLM aracılığıyla güvenli bir SELECT sorgusu üretir, read-only sandbox
içinde çalıştırır ve sonucu pandas DataFrame olarak döndürür.

Akış:
    kullanıcı sorusu + şema JSON
        │
        ▼
    LLM (Gemini) → SELECT sorgusu
        │
        ▼
    _validate_read_only() → sandbox güvenlik filtresi
        │
        ▼
    connector.execute_query() → list[dict]
        │
        ▼
    pandas DataFrame

Kullanım:
    executor = SQLExecutor(db_url="postgresql+psycopg2://user:pass@host/db")
    result   = executor.run("Kategori bazında toplam satışı göster")
    print(result.df)          # pandas DataFrame
    print(result.sql)         # üretilen SQL
    print(result.row_count)   # kaç satır döndü
"""
from __future__ import annotations

import re
import sys

# Windows cmd/PowerShell ASCII modunda başlar; tüm Türkçe çıktıları
# korumak için modül yüklenirken UTF-8'e geç.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dataclasses import dataclass
from typing import Any, cast

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.exc import SQLAlchemyError

from src.agents.llm import get_llm
from src.connectors.base import BaseConnector
from src.connectors.postgres import PostgresConnector
from src.connectors.schema_extractor import schema_to_prompt_string
from src.agents.prompts import SQL_EXECUTOR_SYSTEM_PROMPT
from src.utils.logger import get_logger
from src.utils.metrics import log_token_usage

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Güvenlik: READ-ONLY sandbox
# ---------------------------------------------------------------------------
_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE|MERGE|CALL)\b",
    re.IGNORECASE,
)

# SQL bloğunu LLM yanıtından ayıklamak için (```sql ... ``` veya düz metin)
_SQL_FENCE_PATTERN = re.compile(
    r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE
)

# Maksimum döndürülecek satır sayısı (sandbox güvenlik sınırı)
DEFAULT_ROW_LIMIT = 1000


# ---------------------------------------------------------------------------
# Veri sınıfları
# ---------------------------------------------------------------------------
@dataclass
class SQLExecutionResult:
    """sql_executor.run() çağrısının dönüş değeri."""

    sql: str                          # LLM'in ürettiği / çalıştırılan SQL
    df: pd.DataFrame                  # Sorgu sonucu DataFrame
    row_count: int                    # Dönen satır sayısı
    schema_used: str                  # Prompt'a gömülen şema metni
    error: str | None = None          # Hata varsa mesajı, yoksa None
    raw_llm_response: str = ""        # LLM'in ham yanıtı (debug için)

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class SQLExecutorConfig:
    """SQLExecutor davranışını kontrol eden ayarlar."""

    row_limit: int = DEFAULT_ROW_LIMIT
    # LLM'e ekstra bağlam vermek için ek sistem talimatı (opsiyonel)
    extra_instructions: str = ""


# ---------------------------------------------------------------------------
# Ana sınıf
# ---------------------------------------------------------------------------
class SQLExecutor:
    """
    Text-to-SQL katmanı.

    Args:
        db_url:    SQLAlchemy bağlantı adresi.
                   Örn: "postgresql+psycopg2://user:pass@localhost:5432/mydb"
        connector: Hazır bir BaseConnector nesnesi (db_url yerine kullanılabilir).
        config:    Davranış ayarları (satır limiti vb.).
    """

    def __init__(
        self,
        db_url: str | None = None,
        connector: BaseConnector | None = None,
        config: SQLExecutorConfig | None = None,
    ) -> None:
        if connector is not None:
            self._connector = connector
        elif db_url is not None:
            self._connector = cast(BaseConnector, PostgresConnector(db_url))
        else:
            raise ValueError("db_url veya connector parametrelerinden biri zorunludur.")

        self._llm = get_llm()
        self._config = config or SQLExecutorConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        user_question: str,
        schema_json: dict[str, Any] | None = None,
    ) -> SQLExecutionResult:
        """
        Doğal dil sorusunu SQL'e çevirir, çalıştırır ve DataFrame döndürür.

        Args:
            user_question: Kullanıcının Türkçe/İngilizce sorusu.
            schema_json:   Önceden çıkarılmış şema dict'i (None ise otomatik çekilir).

        Returns:
            SQLExecutionResult — .df, .sql, .success alanlarını içerir.
        """
        # 1. Şema hazırla
        try:
            schema_dict = schema_json or self._connector.extract_schema()
            schema_text = schema_to_prompt_string(schema_dict)
        except Exception as exc:
            logger.error("Şema çıkarma hatası", extra={"error": str(exc)})
            return self._error_result("", "", f"Şema çıkarılamadı: {exc}")

        # Şema boşsa LLM'e gönderme — sistem tablosu sorgulamasını önler
        if not schema_text.strip() or not schema_dict.get("tables"):
            logger.warning("Şema boş — sorgu üretilemiyor")
            return self._error_result(
                "", schema_text,
                "Veritabanında tablo bulunamadı veya şema okunamadı. "
                "Bağlantı bilgilerinizi ve kullanıcı yetkilerini kontrol edin."
            )

        # 2. LLM ile SQL üret
        try:
            raw_response, generated_sql = self._generate_sql(
                user_question, schema_text
            )
        except Exception as exc:
            import traceback
            logger.error(
                "SQL üretim hatası",
                extra={"error": str(exc), "traceback": traceback.format_exc()},
            )
            return self._error_result("", schema_text, f"SQL üretilemedi: {exc}")

        # 3. Read-only sandbox doğrulaması
        try:
            _validate_read_only(generated_sql)
            _validate_no_system_tables(generated_sql)
        except ValueError as exc:
            logger.warning(
                "Güvensiz SQL engellendi",
                extra={"sql": generated_sql, "reason": str(exc)},
            )
            return self._error_result(
                generated_sql, schema_text, f"Güvenlik hatası: {exc}",
                raw_llm_response=raw_response,
            )

        # 4. Sorguyu çalıştır → DataFrame
        try:
            rows = self._connector.execute_query(
                sql=generated_sql,
                limit=self._config.row_limit,
            )
            df = pd.DataFrame(rows)
        except (RuntimeError, SQLAlchemyError) as exc:
            logger.error(
                "Sorgu çalıştırma hatası",
                extra={"sql": generated_sql, "error": str(exc)},
            )
            return self._error_result(
                generated_sql, schema_text, f"Sorgu hatası: {exc}",
                raw_llm_response=raw_response,
            )

        logger.info(
            "SQL çalıştırıldı",
            extra={"row_count": len(df), "sql": generated_sql},
        )

        return SQLExecutionResult(
            sql=generated_sql,
            df=df,
            row_count=len(df),
            schema_used=schema_text,
            raw_llm_response=raw_response,
        )

    # ------------------------------------------------------------------
    # LLM ile SQL üretimi
    # ------------------------------------------------------------------
    def _generate_sql(self, question: str, schema_text: str) -> tuple[str, str]:
        """
        LLM'e sistem prompt + kullanıcı sorusu gönderir, üretilen SQL'i döndürür.

        Returns:
            (ham_yanıt, temizlenmiş_sql)
        """
        system_content = SQL_EXECUTOR_SYSTEM_PROMPT.format(schema=schema_text)
        if self._config.extra_instructions:
            system_content += f"\n\nEK TALİMATLAR:\n{self._config.extra_instructions}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=question),
        ]

        response = self._llm.invoke(messages)
        log_token_usage(response)
        raw: str = _extract_text_content(response.content)
        sql = _extract_sql(raw)

        logger.info("SQL üretildi", extra={"sql": sql})
        return raw, sql

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------
    @staticmethod
    def _error_result(
        sql: str,
        schema_text: str,
        error_msg: str,
        raw_llm_response: str = "",
    ) -> SQLExecutionResult:
        return SQLExecutionResult(
            sql=sql,
            df=pd.DataFrame(),
            row_count=0,
            schema_used=schema_text,
            error=error_msg,
            raw_llm_response=raw_llm_response,
        )


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar (modül düzeyinde — orchestrator'dan da çağrılabilir)
# ---------------------------------------------------------------------------
def _extract_text_content(content) -> str:
    """
    LLM response.content farklı formatlarda gelebilir:
      - str                          → doğrudan döndür
      - list[str]                    → birleştir
      - list[dict]  (Gemini format)  → "text" alanlarını birleştir
    """
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


def _extract_sql(llm_response: str) -> str:
    """
    LLM yanıtından SQL sorgusunu ayıklar.
    Önce ```sql ... ``` bloğunu arar; bulamazsa tüm metni SQL olarak kabul eder.
    """
    match = _SQL_FENCE_PATTERN.search(llm_response)
    if match:
        return match.group(1).strip()
    # Kod bloğu yoksa yanıtın kendisini döndür (gereksiz boşlukları temizle)
    return llm_response.strip()


def _validate_no_system_tables(sql: str) -> None:
    """
    SQLite / PostgreSQL sistem tablolarına yönelik sorguları engeller.
    LLM yanlış dialect seçtiğinde bu filtre devreye girer.
    """
    forbidden_patterns = re.compile(
        r"\b(sqlite_master|sqlite_sequence|sqlite_stat\d*"
        r"|pg_catalog|pg_tables|pg_class|pg_namespace"
        r"|sysobjects|sys\.tables|sys\.columns"
        r")\b",
        re.IGNORECASE,
    )
    if forbidden_patterns.search(sql):
        raise ValueError(
            "Sistem tablosu sorgusu engellendi. "
            "Yalnızca veritabanı şemasındaki tablolara sorgu yapılabilir."
        )


def _validate_read_only(sql: str) -> None:
    """
    Yalnızca SELECT sorgularına izin verir.
    Tehlikeli anahtar kelime veya yanlış başlangıç tespit edilirse ValueError fırlatır.
    """
    stripped = sql.strip().rstrip(";")

    if not stripped:
        raise ValueError("SQL sorgusu boş.")

    if _FORBIDDEN_PATTERN.search(stripped):
        raise ValueError(
            "Yalnızca SELECT sorgularına izin verilir. "
            "Değiştirici (INSERT/UPDATE/DELETE/DROP vb.) komutlar yasaktır."
        )

    first_word = stripped.split()[0].upper()
    if first_word not in {"SELECT", "WITH"}:
        # WITH ... SELECT (CTE) yapısına da izin ver
        raise ValueError(
            f"Sorgu SELECT veya WITH ile başlamalıdır. "
            f"Bulunan ilk kelime: '{first_word}'"
        )


# ---------------------------------------------------------------------------
# Hızlı test — python -m src.agents.tools.sql_executor
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    from pathlib import Path

    # Python'un tüm IO işlemlerini UTF-8'e zorla (Windows için kritik)
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parents[4]
    load_dotenv(project_root / ".env")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL .env dosyasında tanımlı değil; test atlandı.")
    else:
        executor = SQLExecutor(db_url=db_url)
        soru = "Her tablodan ilk 5 satırı göster"
        print(f"\nSoru: {soru}")
        result = executor.run(soru)

        if result.success:
            print(f"\nÜretilen SQL:\n{result.sql}")
            print(f"\nDönen satır sayısı: {result.row_count}")
            print(f"\nDataFrame (ilk 5 satır):\n{result.df.head()}")
        else:
            print(f"\nHata: {result.error}")
