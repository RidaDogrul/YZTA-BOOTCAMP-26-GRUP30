"""
Şema Keşif Motoru (Görev S1-O1)
--------------------------------
Bir veritabanına bağlanır; tabloları, sütunları, veri tiplerini, birincil
anahtarları (PK) ve yabancı anahtar (FK) ilişkilerini çıkarır. Ardından bu
bilgiyi LLM'in kolayca okuyabileceği temiz bir yapıya dönüştürür.

Bu modülün çıktısı, daha önce yazdığın prompts.py içindeki
SQL_EXECUTOR_SYSTEM_PROMPT'un {schema} alanını dolduracak.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import create_engine, inspect


def extract_schema(db_url: str) -> dict[str, Any]:
    """
    Verilen veritabanındaki tüm tabloların meta-verisini çıkarır.

    Args:
        db_url: SQLAlchemy bağlantı adresi. Örnekler:
                "postgresql+psycopg2://user:pass@localhost:5432/mydb"
                "mysql+pymysql://user:pass@localhost:3306/mydb"
                "sqlite:///./demo.db"

    Returns:
        Tabloları, sütunları ve ilişkileri içeren yapılandırılmış bir dict.
    """
    engine = create_engine(db_url)
    inspector = inspect(engine)

    tables: list[dict[str, Any]] = []

    for table_name in inspector.get_table_names():
        # Birincil anahtar sütunlarını bir kümede topla (hızlı kontrol için)
        pk_info = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_info.get("constrained_columns", []))

        # --- Sütun bilgileri ---
        columns: list[dict[str, Any]] = []
        for col in inspector.get_columns(table_name):
            columns.append(
                {
                    "name": col["name"],
                    "type": str(col["type"]),       # örn: "VARCHAR(255)", "INTEGER"
                    "nullable": col.get("nullable", True),
                    "primary_key": col["name"] in pk_columns,
                }
            )

        # --- Yabancı anahtar (FK) ilişkileri ---
        foreign_keys: list[dict[str, Any]] = []
        for fk in inspector.get_foreign_keys(table_name):
            foreign_keys.append(
                {
                    "columns": fk.get("constrained_columns", []),
                    "references_table": fk.get("referred_table"),
                    "references_columns": fk.get("referred_columns", []),
                }
            )

        tables.append(
            {
                "table_name": table_name,
                "columns": columns,
                "foreign_keys": foreign_keys,
            }
        )

    engine.dispose()
    return {"tables": tables}


def schema_to_prompt_string(schema: dict[str, Any]) -> str:
    """
    extract_schema çıktısını, LLM prompt'una gömmek için kısa ve okunaklı
    bir metne çevirir. JSON'a göre çok daha az token harcar.
    """
    lines: list[str] = []

    for table in schema["tables"]:
        lines.append(f"Tablo: {table['table_name']}")

        for col in table["columns"]:
            flags = []
            if col["primary_key"]:
                flags.append("PK")
            if not col["nullable"]:
                flags.append("NOT NULL")
            flag_text = f"  [{', '.join(flags)}]" if flags else ""
            lines.append(f"  - {col['name']}: {col['type']}{flag_text}")

        for fk in table["foreign_keys"]:
            src = ", ".join(fk["columns"])
            ref = ", ".join(fk["references_columns"])
            lines.append(f"  FK: {src} -> {fk['references_table']}({ref})")

        lines.append("")  # tablolar arası boş satır

    return "\n".join(lines).strip()


# --- Hızlı test ---
# Gerçek bir veritabanı kurmadan denemek için geçici bir SQLite DB oluşturuyoruz.
# Çalıştır:  python -m src.connectors.schema_extractor
if __name__ == "__main__":
    from sqlalchemy import text

    demo_url = "sqlite:///./demo.db"

    # İlişkili iki örnek tablo oluştur (customers <- orders)
    demo_engine = create_engine(demo_url)
    with demo_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id    INTEGER PRIMARY KEY,
                    name  TEXT NOT NULL,
                    email TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id          INTEGER PRIMARY KEY,
                    customer_id INTEGER NOT NULL,
                    amount      REAL,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
                """
            )
        )
    demo_engine.dispose()

    # Şemayı çıkar ve iki formatta da yazdır
    result = extract_schema(demo_url)

    print("=== JSON meta-data ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n=== LLM prompt formatı ===")
    print(schema_to_prompt_string(result))