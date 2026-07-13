"""

AI Agent Orchestrator (Görev S2-H1)
-----------------------------------
Kullanıcının sorusunu alır ve iki ajanı SIRAYLA çalıştırır:
  Agent 1 (Veri Çekme)     → veriyi getirir (SQL veya MongoDB)
  Agent 2 (Data Scientist) → veriyi temizler (null doldurma + outlier işleme)

Orchestrator, connector tipine bakıp doğru Agent 1'i otomatik seçer:
  - SQL connector (Postgres/MySQL) → SQLExecutor (Text-to-SQL)
  - Mongo connector               → find_documents (koleksiyon → DataFrame)

Agent 2 (temizleme) her iki yol için de AYNIDIR; bir DataFrame alır, temiz
DataFrame döndürür — verinin kaynağını umursamaz.

Kullanım:
    # Postgres:
    orch = Orchestrator(db_url="postgresql+psycopg2://user:pass@host/db")
    result = orch.run("Kategori bazında toplam satışı göster")

    # MySQL:
    from src.connectors.mysql import MySQLConnector
    orch = Orchestrator(connector=MySQLConnector("mysql+pymysql://root:test@localhost:3306/demo"))
    result = orch.run("customers tablosundaki kayıtları göster")

    # MongoDB (MVP: koleksiyon çekilir, temizlenir):
    from src.connectors.mongodb import MongoConnector
    orch = Orchestrator(connector=MongoConnector("mongodb://localhost:27017/demo"))
    result = orch.run("verileri analiz et", collection="customers")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import pandas as pd

from src.agents.tools.sql_executor import SQLExecutor
from src.connectors.base import BaseConnector
from src.ml_models.preprocessor import DataCleaningPipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_ROW_LIMIT = 1000


# ---------------------------------------------------------------------------
# Sonuç veri sınıfı
# ---------------------------------------------------------------------------
@dataclass
class OrchestratorResult:
    """orchestrator.run() çağrısının tüm adımlarını içeren birleşik sonuç."""

    question: str                                                   # kullanıcının sorusu
    query: str = ""                                                 # çalıştırılan sorgu (SQL veya Mongo açıklaması)
    source: str = ""                                                # "sql" | "mongo"
    raw_df: pd.DataFrame = field(default_factory=pd.DataFrame)      # temizlenmemiş veri
    cleaned_df: pd.DataFrame = field(default_factory=pd.DataFrame)  # Agent 2 çıktısı
    cleaning_summary: str = ""                                      # temizleme raporu (metin)
    row_count: int = 0                                              # temiz veri satır sayısı
    error: str | None = None                                       # hata varsa mesajı
    failed_stage: str | None = None                                # hata hangi adımda oldu

    @property
    def success(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Orchestrator:
    """
    İki ajanlı iş akışını yöneten sınıf. SQL (Postgres/MySQL) ve MongoDB destekler.

    Args:
        db_url: SQLAlchemy bağlantı adresi (Postgres). MySQL için 'connector' geçir.
        connector: Hazır connector — SQL (BaseConnector) veya Mongo (MongoConnector).
        cleaning_pipeline: Özel DataCleaningPipeline (verilmezse varsayılan kurulur).
    """

    def __init__(
        self,
        db_url: str | None = None,
        connector: object | None = None,
        cleaning_pipeline: DataCleaningPipeline | None = None,
    ) -> None:
        self._cleaning_pipeline = cleaning_pipeline or DataCleaningPipeline()
        self._sql_executor: SQLExecutor | None = None
        self._mongo: object | None = None
        self._row_limit = DEFAULT_ROW_LIMIT

        # --- Connector tipini algıla ve doğru Agent 1'i seç ---
        # Duck-typing: Mongo connector'da find_documents metodu vardır.
        if connector is not None and hasattr(connector, "find_documents"):
            self._mode = "mongo"
            self._mongo = connector
        elif connector is not None or db_url is not None:
            self._mode = "sql"
            # Bu dala girdiysek connector ya None ya da bir SQL BaseConnector'dır.
            sql_connector = cast("BaseConnector | None", connector)
            self._sql_executor = SQLExecutor(db_url=db_url, connector=sql_connector)
        else:
            raise ValueError("connector veya db_url parametrelerinden biri zorunludur.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        user_question: str,
        collection: str | None = None,
    ) -> OrchestratorResult:
        """
        Soruyu iki ajandan geçirir ve birleşik sonucu döndürür.

        Args:
            user_question: Kullanıcının sorusu (SQL modunda SQL'e çevrilir).
            collection: Yalnızca Mongo modunda kullanılır. None ise ilk koleksiyon.

        Bir adım başarısız olursa sonraki adıma geçmez; hangi adımda hata olduğunu
        raporlar (bu, hata ayıklamayı ve şeffaflığı kolaylaştırır).
        """
        result = OrchestratorResult(question=user_question, source=self._mode)

        # -------------------- Agent 1: Veri çekme --------------------
        if self._mode == "sql":
            ok = self._run_sql_agent(user_question, result)
        else:
            ok = self._run_mongo_agent(collection, result)

        if not ok:
            return result  # Agent 1 başarısız; hata result içinde işaretlendi

        # Sonuç boşsa temizlemeye gerek yok — erken çık.
        if result.raw_df.empty:
            logger.info("Agent 1 boş sonuç döndürdü; temizleme atlanıyor.")
            result.cleaned_df = result.raw_df
            result.cleaning_summary = "Veri boş olduğu için temizleme yapılmadı."
            return result

        # -------------------- Agent 2: Data Scientist --------------------
        logger.info("Agent 2 (Data Scientist) başlıyor", extra={"rows": len(result.raw_df)})
        try:
            cleaned_df = self._cleaning_pipeline.fit_transform(result.raw_df)
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent 2 başarısız", extra={"error": str(exc)})
            # Agent 2 çökse bile ham veriyi kaybetme.
            result.cleaned_df = result.raw_df
            result.row_count = len(result.raw_df)
            result.error = f"Veri temizleme hatası: {exc}"
            result.failed_stage = "data_scientist"
            return result

        result.cleaned_df = cleaned_df
        result.row_count = len(cleaned_df)
        result.cleaning_summary = self._cleaning_pipeline.report_.summary()

        logger.info("Orchestrator tamamlandı", extra={"final_rows": result.row_count})
        return result

    # ------------------------------------------------------------------
    # Agent 1 uygulamaları
    # ------------------------------------------------------------------
    def _run_sql_agent(self, question: str, result: OrchestratorResult) -> bool:
        """SQL yolu: Text-to-SQL ile veri çeker. Başarılıysa True döner."""
        logger.info("Agent 1 (SQL Executor) başlıyor", extra={"question": question})
        sql_result = self._sql_executor.run(question)  # type: ignore[union-attr]

        result.query = sql_result.sql
        result.raw_df = sql_result.df

        if not sql_result.success:
            logger.error("Agent 1 (SQL) başarısız", extra={"error": sql_result.error})
            result.error = sql_result.error
            result.failed_stage = "sql_executor"
            return False
        return True

    def _run_mongo_agent(self, collection: str | None, result: OrchestratorResult) -> bool:
        """
        Mongo yolu (MVP): bir koleksiyonu DataFrame'e çeker. Başarılıysa True döner.
        Not: Bu MVP'de doğal dil sorusu koleksiyon seçimine dönüşür; tam
        Text-to-MongoQuery ileride eklenebilir.
        """
        logger.info("Agent 1 (Mongo Fetch) başlıyor", extra={"collection": collection})
        try:
            # Koleksiyon belirtilmemişse ilkini kullan.
            if collection is None:
                collections = self._mongo.list_collections()  # type: ignore[union-attr]
                if not collections:
                    raise RuntimeError("Veritabanında hiç koleksiyon yok.")
                collection = collections[0]
                logger.info("Koleksiyon belirtilmedi; ilki kullanılıyor",
                            extra={"collection": collection})

            rows = self._mongo.find_documents(collection, limit=self._row_limit)  # type: ignore[union-attr]
            result.raw_df = pd.DataFrame(rows)
            result.query = f"MongoDB find → koleksiyon: {collection} (limit={self._row_limit})"
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent 1 (Mongo) başarısız", extra={"error": str(exc)})
            result.error = f"Mongo veri çekme hatası: {exc}"
            result.failed_stage = "mongo_fetch"
            return False


# ---------------------------------------------------------------------------
# Hızlı test — python -m src.agents.orchestrator
# Üç veritabanını da destekler: .env'de hangisi tanımlıysa onu kullanır.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    postgres_url = os.getenv("DATABASE_URL")
    mysql_url = os.getenv("MYSQL_URL")
    mongo_uri = os.getenv("MONGODB_URI")

    orchestrator = None
    collection = None
    soru = "verileri getir ve analiz et"

    if postgres_url:
        orchestrator = Orchestrator(db_url=postgres_url)
        soru = "Her tablodan ilk 5 satırı göster"
    elif mysql_url:
        from src.connectors.mysql import MySQLConnector
        orchestrator = Orchestrator(connector=MySQLConnector(mysql_url))
        soru = "customers tablosundaki tüm kayıtları göster"
    elif mongo_uri:
        from src.connectors.mongodb import MongoConnector
        orchestrator = Orchestrator(connector=MongoConnector(mongo_uri))
        # collection=None → ilk koleksiyon otomatik seçilir
    else:
        print("Hiçbir veritabanı .env'de tanımlı değil "
              "(DATABASE_URL / MYSQL_URL / MONGODB_URI).")

    if orchestrator is not None:
        print(f"\nKaynak: {orchestrator._mode}")
        print(f"Soru: {soru}\n")

        result = orchestrator.run(soru, collection=collection)

        if result.success:
            print(f"Çalıştırılan sorgu:\n{result.query}\n")
            print(f"Ham veri boyutu   : {result.raw_df.shape}")
            print(f"Temiz veri boyutu : {result.cleaned_df.shape}\n")
            print(result.cleaning_summary)
            print(f"\nİlk satırlar:\n{result.cleaned_df.head()}")
        else:
            print(f"HATA ({result.failed_stage}): {result.error}")