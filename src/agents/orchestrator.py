"""

AI Agent Orchestrator (Task S2-H1)
-----------------------------------
Kullanıcının sorusunu alır ve iki ajanı SIRAYLA çalıştırır:
  Agent 1 (Veri Çekme)     → veriyi getirir (SQL / MongoDB / S3)
  Agent 2 (Data Scientist) → veriyi temizler (null doldurma + outlier işleme)

Orchestrator, connector tipine bakıp doğru Agent 1'i otomatik seçer:
  - SQL connector (Postgres/MySQL/Snowflake) → SQLExecutor (Text-to-SQL)
  - Mongo connector  → find_documents (koleksiyon → DataFrame)
  - S3 connector     → ilk veri dosyasını indir → DataFrame

Agent 2 (DataScientistAgent) tüm yollar için AYNIDIR; bir DataFrame alır,
temiz DataFrame + yapısal rapor döndürür.

Kullanım:
    # Postgres:
    orch = Orchestrator(db_url="postgresql+psycopg2://user:pass@host/db")
    result = orch.run("Kategori bazında toplam satışı göster")

    # MySQL:
    from src.connectors.mysql import MySQLConnector
    orch = Orchestrator(connector=MySQLConnector("mysql+pymysql://root:test@localhost:3306/demo"))
    result = orch.run("customers tablosundaki kayıtları göster")

    # MongoDB:
    from src.connectors.mongodb import MongoConnector
    orch = Orchestrator(connector=MongoConnector("mongodb://localhost:27017/demo"))
    result = orch.run("verileri analiz et", collection="customers")

    # S3:
    from src.connectors.s3_storage import S3Config, S3Connector
    orch = Orchestrator(connector=S3Connector(config))
    result = orch.run("satış verisini analiz et")
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import cast

import pandas as pd

from src.agents.data_scientist import DataScientistAgent
from src.agents.tools.sql_executor import SQLExecutor
from src.connectors.base import BaseConnector
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_ROW_LIMIT = 1000


# ---------------------------------------------------------------------------
# Sonuç veri sınıfı
# ---------------------------------------------------------------------------
@dataclass
class OrchestratorResult:
    """orchestrator.run() çağrısının tüm adımlarını içeren birleşik sonuç."""

    question: str
    query: str = ""
    source: str = ""
    raw_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    cleaned_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    cleaning_summary: str = ""
    cleaning_report: dict = field(default_factory=dict)
    row_count: int = 0
    error: str | None = None
    failed_stage: str | None = None

    # S3'e özgü: her dosya ayrı DataFrame olarak saklanır
    # key: dosya adı (stem), value: temizlenmiş DataFrame
    s3_tables: dict[str, pd.DataFrame] = field(default_factory=dict)

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
        data_scientist: Özel DataScientistAgent (verilmezse varsayılan kurulur).
    """

    def __init__(
        self,
        db_url: str | None = None,
        connector: object | None = None,
        data_scientist: DataScientistAgent | None = None,
    ) -> None:
        self._data_scientist = data_scientist or DataScientistAgent()
        self._sql_executor: SQLExecutor | None = None
        self._mongo: object | None = None
        self._s3: object | None = None
        self._row_limit = DEFAULT_ROW_LIMIT

        # --- Connector tipini algıla ve doğru Agent 1'i seç ---
        # Duck-typing: Mongo connector'da find_documents metodu vardır.
        if connector is not None and hasattr(connector, "find_documents"):
            self._mode = "mongo"
            self._mongo = connector
        # Duck-typing: S3 connector'da list_data_files metodu vardır.
        elif connector is not None and hasattr(connector, "list_data_files"):
            self._mode = "s3"
            self._s3 = connector
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
        elif self._mode == "mongo":
            ok = self._run_mongo_agent(collection, result)
        else:  # s3
            ok = self._run_s3_agent(result)

        if not ok:
            return result

        # Sonuç boşsa temizlemeye gerek yok — erken çık.
        if result.raw_df.empty and not result.s3_tables:
            logger.info("Agent 1 boş sonuç döndürdü; temizleme atlanıyor.")
            result.cleaned_df = result.raw_df
            result.cleaning_summary = "Veri boş olduğu için temizleme yapılmadı."
            return result

        # -------------------- Agent 2: Data Scientist --------------------
        if self._mode == "s3" and result.s3_tables:
            # Her tabloyu ayrı ayrı temizle
            summaries: list[str] = []
            for name, df in result.s3_tables.items():
                cleaning = self._data_scientist.run(df)
                result.s3_tables[name] = cleaning.cleaned_df
                summaries.append(f"[{name}] {cleaning.summary}")
                if not cleaning.success:
                    logger.warning("Tablo temizleme kısmen başarısız",
                                   extra={"table": name, "error": cleaning.error})
            result.cleaning_summary = "\n".join(summaries)
            result.row_count = sum(len(df) for df in result.s3_tables.values())
            # cleaned_df = birleşik (sadece LLM preview için)
            result.cleaned_df = pd.concat(
                list(result.s3_tables.values()), ignore_index=True, sort=False
            )
        else:
            cleaning = self._data_scientist.run(result.raw_df)
            result.cleaned_df = cleaning.cleaned_df
            result.row_count = len(cleaning.cleaned_df)
            result.cleaning_summary = cleaning.summary
            result.cleaning_report = cleaning.report
            if not cleaning.success:
                result.error = cleaning.error
                result.failed_stage = "data_scientist"
                return result

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
        """
        logger.info("Agent 1 (Mongo Fetch) başlıyor", extra={"collection": collection})
        try:
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

    def _run_s3_agent(self, result: OrchestratorResult) -> bool:
        """
        S3 yolu: Bucket'taki desteklenen veri dosyalarını listeler.

        Seçim mantığı (öncelik sırası):
          1. Kullanıcı sorusunda dosya adı geçiyorsa o/birkaç dosyayı seç.
          2. Soru "birleştir / join / merge / hepsini" içeriyorsa tümünü seç.
          3. Aksi hâlde her dosyayı AYRI tablo olarak yükle (concat YOK).

        Desteklenen formatlar: .csv, .tsv, .json, .jsonl, .parquet, .xlsx, .xls
        """
        logger.info("Agent 1 (S3 Fetch) başlıyor")
        try:
            files = self._s3.list_data_files(max_keys=200)  # type: ignore[union-attr]
            if not files:
                raise RuntimeError(
                    "Bucket'ta desteklenen veri dosyası bulunamadı "
                    "(.csv, .json, .parquet, .xlsx vb.)."
                )

            logger.info(
                "S3 dosyaları listelendi",
                extra={"count": len(files), "keys": [f["key"] for f in files]},
            )

            question_lower = result.question.lower()

            # Dosya adı eşleşmesi
            matched = [
                f for f in files
                if _file_stem(f["key"]).lower() in question_lower
                or _file_stem(f["key"]).lower().replace("_", " ") in question_lower
            ]
            selected = matched if matched else files

            logger.info("S3 dosyaları seçildi",
                        extra={"keys": [f["key"] for f in selected]})

            # Her dosyayı ayrı DataFrame'e yükle
            loaded_keys: list[str] = []
            for f in selected:
                key = f["key"]
                ext = f["extension"].lower()
                stem = _file_stem(key)
                try:
                    raw_bytes = self._s3.download_bytes(key)  # type: ignore[union-attr]
                    df = _s3_bytes_to_df(raw_bytes, ext, key)
                    # _source_file kolonu (birleştirme için hazırlık)
                    df["_source_file"] = stem
                    result.s3_tables[stem] = df
                    loaded_keys.append(key)
                    logger.info("S3 dosyası yüklendi",
                                extra={"key": key, "rows": len(df)})
                except Exception as file_exc:  # noqa: BLE001
                    logger.warning("S3 dosyası atlandı",
                                   extra={"key": key, "error": str(file_exc)})

            if not result.s3_tables:
                raise RuntimeError(
                    f"Hiçbir dosya okunamadı: {[f['key'] for f in selected]}"
                )

            # raw_df = ilk tablonun özeti (geriye dönük uyumluluk)
            first_name = next(iter(result.s3_tables))
            result.raw_df = result.s3_tables[first_name]

            table_info = ", ".join(
                f"{name}({len(df)} satır)"
                for name, df in result.s3_tables.items()
            )
            result.query = (
                f"S3 → {len(loaded_keys)} tablo yüklendi: {table_info}"
            )
            return True

        except Exception as exc:  # noqa: BLE001
            logger.error("Agent 1 (S3) başarısız", extra={"error": str(exc)})
            result.error = f"S3 veri çekme hatası: {exc}"
            result.failed_stage = "s3_fetch"
            return False


# ---------------------------------------------------------------------------
# S3 format dönüştürücü ve yardımcılar (modül seviyesi)
# ---------------------------------------------------------------------------
def _file_stem(key: str) -> str:
    """
    S3 nesne anahtarından uzantısız dosya adını çıkarır.
    Örn: "data/orders_raw.xlsx" → "orders_raw"
    """
    name = key.split("/")[-1]       # klasör yolunu at
    dot = name.rfind(".")
    return name[:dot] if dot > 0 else name


def _s3_bytes_to_df(raw: bytes, ext: str, key: str) -> pd.DataFrame:
    """Ham baytları dosya uzantısına göre DataFrame'e çevirir."""
    buf = io.BytesIO(raw)
    buf.seek(0)  # S3 download sonrası pozisyonu sıfırla

    if ext in (".csv", ".tsv"):
        sep = "\t" if ext == ".tsv" else ","
        return pd.read_csv(buf, sep=sep)
    if ext == ".json":
        return pd.read_json(buf)
    if ext == ".jsonl":
        return pd.read_json(buf, lines=True)
    if ext == ".parquet":
        return pd.read_parquet(buf)
    if ext == ".xlsx":
        return pd.read_excel(buf, engine="openpyxl")
    if ext == ".xls":
        return pd.read_excel(buf, engine="xlrd")
    raise ValueError(f"Desteklenmeyen dosya formatı: {ext} ({key})")


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
            print(f"\nYapısal rapor: {result.cleaning_report}")
            print(f"\nİlk satırlar:\n{result.cleaned_df.head()}")
        else:
            print(f"HATA ({result.failed_stage}): {result.error}")