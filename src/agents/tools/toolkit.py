"""

Ajan Araçları (Tools) Modülü — Task S2-O4
------------------------------------------
Orchestrator'ın (ve ileride bir LangChain AgentExecutor'ın) çağırabileceği,
tek sorumluluklu, belgelenmiş Python fonksiyon araçları.

Tasarım deseni: 'build_tools(connector)' bir FABRİKA fonksiyonudur. Connector'ı
bir closure ile sarar ve dışarıya yalnızca basit argüman (string/sayı) alan
LangChain tool'ları döndürür. Böylece:
  - Orchestrator tool'ları doğrudan çağırabilir.
  - Bir LangChain agent'ı bunları LLM'e verip aracı seçtirebilir.

Connector tipine göre farklı araçlar üretilir:
  - SQL connector (Postgres/MySQL) → get_database_schema, run_sql_query, clean_dataset
  - Mongo connector                → get_database_schema, fetch_mongo_collection, clean_dataset
"""
from __future__ import annotations

import json

import pandas as pd
from langchain_core.tools import StructuredTool

from src.ml_models.preprocessor import DataCleaningPipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_ROW_LIMIT = 1000


def build_tools(connector: object) -> list[StructuredTool]:
    """
    Verilen connector'a bağlı LangChain tool listesini üretir.

    Args:
        connector: SQL (BaseConnector) veya Mongo (MongoConnector) nesnesi.

    Returns:
        Connector tipine uygun StructuredTool listesi.
    """
    # Mongo connector'da find_documents metodu vardır; SQL'de execute_query.
    is_mongo = hasattr(connector, "find_documents")

    # ----------------------------------------------------------------
    # Araç 1: Şema getir (her iki DB tipinde de var)
    # ----------------------------------------------------------------
    def get_database_schema() -> str:
        """Veritabanının şemasını (tablolar/koleksiyonlar, sütunlar, tipler,
        ilişkiler) LLM'in okuyabileceği metin olarak döndürür."""
        logger.info("Tool çağrıldı: get_database_schema")
        return connector.schema_to_prompt()  # type: ignore[attr-defined]

    tools: list[StructuredTool] = [
        StructuredTool.from_function(
            func=get_database_schema,
            name="get_database_schema",
            description=(
                "Veritabanı şemasını döndürür. SQL sorgusu veya koleksiyon "
                "seçimi yapmadan ÖNCE hangi tabloların/sütunların var olduğunu "
                "öğrenmek için kullan."
            ),
        )
    ]

    # ----------------------------------------------------------------
    # Araç 2a: SQL çalıştır (yalnızca SQL connector için)
    # ----------------------------------------------------------------
    if not is_mongo:

        def run_sql_query(sql: str) -> str:
            """Salt-okunur (SELECT) bir SQL sorgusu çalıştırır ve sonucu
            JSON kayıt listesi olarak döndürür. Yazma sorguları reddedilir."""
            logger.info("Tool çağrıldı: run_sql_query", extra={"sql": sql})
            # execute_query, BaseConnector içinde read-only doğrulaması yapar.
            rows = connector.execute_query(sql)  # type: ignore[attr-defined]
            return json.dumps(rows, ensure_ascii=False, default=str)

        tools.append(
            StructuredTool.from_function(
                func=run_sql_query,
                name="run_sql_query",
                description=(
                    "Salt-okunur bir SQL SELECT sorgusu çalıştırır ve sonucu "
                    "JSON olarak döndürür. Sadece SELECT; INSERT/UPDATE/DELETE "
                    "kabul edilmez."
                ),
            )
        )

    # ----------------------------------------------------------------
    # Araç 2b: Koleksiyon çek (yalnızca Mongo connector için)
    # ----------------------------------------------------------------
    else:

        def fetch_mongo_collection(collection: str, limit: int = DEFAULT_ROW_LIMIT) -> str:
            """Bir MongoDB koleksiyonundaki belgeleri getirir ve JSON kayıt
            listesi olarak döndürür."""
            logger.info(
                "Tool çağrıldı: fetch_mongo_collection",
                extra={"collection": collection, "limit": limit},
            )
            rows = connector.find_documents(collection, limit=limit)  # type: ignore[attr-defined]
            return json.dumps(rows, ensure_ascii=False, default=str)

        tools.append(
            StructuredTool.from_function(
                func=fetch_mongo_collection,
                name="fetch_mongo_collection",
                description=(
                    "Belirtilen MongoDB koleksiyonundaki belgeleri getirir ve "
                    "JSON olarak döndürür. Önce get_database_schema ile "
                    "koleksiyon adlarını öğren."
                ),
            )
        )

    # ----------------------------------------------------------------
    # Araç 3: Veri temizle (connector'dan bağımsız — her iki tip için de eklenir)
    # ----------------------------------------------------------------
    def clean_dataset(records_json: str) -> str:
        """JSON kayıt listesi alır, null doldurma + outlier işleme uygular ve
        {"cleaned_records": [...], "report": "..."} JSON'u döndürür."""
        logger.info("Tool çağrıldı: clean_dataset")
        records = json.loads(records_json)
        df = pd.DataFrame(records)

        if df.empty:
            return json.dumps(
                {"cleaned_records": [], "report": "Veri boş; temizleme yapılmadı."},
                ensure_ascii=False,
            )

        pipeline = DataCleaningPipeline()
        cleaned = pipeline.fit_transform(df)
        return json.dumps(
            {
                "cleaned_records": json.loads(cleaned.to_json(orient="records")),
                "report": pipeline.report_.summary(),
            },
            ensure_ascii=False,
            default=str,
        )

    tools.append(
        StructuredTool.from_function(
            func=clean_dataset,
            name="clean_dataset",
            description=(
                "JSON kayıt listesindeki eksik (null) ve aykırı (outlier) "
                "değerleri temizler. run_sql_query veya fetch_mongo_collection "
                "çıktısını buraya verebilirsin."
            ),
        )
    )

    return tools


# ---------------------------------------------------------------------------
# Hızlı test — python -m src.agents.tools.toolkit
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env")

    mysql_url = os.getenv("MYSQL_URL")
    if not mysql_url:
        print("MYSQL_URL .env dosyasında tanımlı değil; test atlandı.")
    else:
        from src.connectors.mysql import MySQLConnector

        connector = MySQLConnector(mysql_url)
        tools = build_tools(connector)

        print("Kullanılabilir araçlar:", [t.name for t in tools])

        # 1) Şema aracı
        schema_tool = next(t for t in tools if t.name == "get_database_schema")
        print("\n--- get_database_schema ---")
        print(schema_tool.invoke({}))

        # 2) SQL aracı
        sql_tool = next(t for t in tools if t.name == "run_sql_query")
        print("\n--- run_sql_query ---")
        raw = sql_tool.invoke({"sql": "SELECT * FROM customers LIMIT 3"})
        print(raw)

        # 3) Temizleme aracı (SQL çıktısını doğrudan besle)
        clean_tool = next(t for t in tools if t.name == "clean_dataset")
        print("\n--- clean_dataset ---")
        print(clean_tool.invoke({"records_json": raw}))

        connector.close()