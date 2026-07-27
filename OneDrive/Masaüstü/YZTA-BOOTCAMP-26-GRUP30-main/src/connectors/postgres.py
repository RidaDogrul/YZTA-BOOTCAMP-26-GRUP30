"""
PostgreSQL Konnektörü (Görev 1.1)
---------------------------------
PostgreSQL veritabanlarına güvenli bağlantı kurar; şema keşfi ve
salt-okunur (SELECT) sorgu çalıştırma işlemlerini yönetir.

Şema çıkarma işlemi src.connectors.schema_extractor modülüne devredilir.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Any, Generator

from pydantic import BaseModel, Field, SecretStr, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.connectors.schema_extractor import extract_schema, schema_to_prompt_string

# Yalnızca okuma amaçlı sorgulara izin verilir (prompts.py ile uyumlu).
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class PostgresConfig(BaseModel):
    """PostgreSQL bağlantı parametreleri."""

    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    database: str
    user: str
    password: SecretStr
    sslmode: str | None = None

    @field_validator("database", "user")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Alan boş olamaz.")
        return value

    def to_url(self) -> str:
        """SQLAlchemy bağlantı adresini üretir."""
        password = self.password.get_secret_value()
        url = (
            f"postgresql+psycopg2://{self.user}:{password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
        if self.sslmode:
            url += f"?sslmode={self.sslmode}"
        return url

    @classmethod
    def from_url(cls, db_url: str) -> "PostgresConfig":
        """
        Tam SQLAlchemy URL'sinden konfigürasyon oluşturur.
        Örnek: postgresql+psycopg2://user:pass@localhost:5432/mydb
        """
        pattern = (
            r"^postgresql(?:\+psycopg2)?://"
            r"(?P<user>[^:@/]+)(?::(?P<password>[^@]*))?@"
            r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/"
            r"(?P<database>[^?]+)"
            r"(?:\?sslmode=(?P<sslmode>[^&]+))?"
        )
        match = re.match(pattern, db_url)
        if not match:
            raise ValueError("Geçersiz PostgreSQL bağlantı adresi.")

        groups = match.groupdict()
        return cls(
            host=groups["host"],
            port=int(groups["port"] or 5432),
            database=groups["database"],
            user=groups["user"],
            password=SecretStr(groups["password"] or ""),
            sslmode=groups.get("sslmode"),
        )


class PostgresConnector:
    """PostgreSQL veritabanı konnektörü."""

    def __init__(self, config: PostgresConfig | str) -> None:
        if isinstance(config, str):
            self.config = PostgresConfig.from_url(config)
        else:
            self.config = config
        self._engine: Engine | None = None

    @property
    def db_url(self) -> str:
        return self.config.to_url()

    def connect(self) -> Engine:
        """Bağlantı havuzunu oluşturur veya mevcut olanı döndürür."""
        if self._engine is None:
            self._engine = create_engine(
                self.db_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    def close(self) -> None:
        """Açık bağlantıları kapatır."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    @contextmanager
    def session(self) -> Generator[Engine, None, None]:
        """Bağlantıyı otomatik kapatacak context manager."""
        engine = self.connect()
        try:
            yield engine
        finally:
            self.close()

    def test_connection(self) -> dict[str, Any]:
        """
        Veritabanına bağlanılabildiğini doğrular.

        Returns:
            {"ok": True/False, "message": "...", "version": "..." (başarılıysa)}
        """
        try:
            engine = self.connect()
            with engine.connect() as conn:
                version = conn.execute(text("SELECT version()")).scalar()
            return {
                "ok": True,
                "message": "PostgreSQL bağlantısı başarılı.",
                "version": version,
            }
        except SQLAlchemyError as exc:
            return {
                "ok": False,
                "message": f"Bağlantı hatası: {exc}",
            }

    def extract_schema(self) -> dict[str, Any]:
        """Tablo, sütun ve ilişki meta-verisini çıkarır."""
        try:
            return extract_schema(self.db_url)
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Şema çıkarılamadı: {exc}") from exc

    def schema_to_prompt(self) -> str:
        """LLM prompt'u için okunaklı şema metni üretir."""
        return schema_to_prompt_string(self.extract_schema())

    @staticmethod
    def _validate_read_only(sql: str) -> None:
        """Yalnızca SELECT sorgularına izin verir."""
        stripped = sql.strip().rstrip(";")
        if not stripped:
            raise ValueError("SQL sorgusu boş olamaz.")

        if _FORBIDDEN_SQL.search(stripped):
            raise ValueError(
                "Yalnızca okuma (SELECT) sorgularına izin verilir."
            )

        if not stripped.upper().lstrip().startswith("SELECT"):
            raise ValueError("Sorgu SELECT ile başlamalıdır.")

    def execute_query(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Salt-okunur SQL sorgusu çalıştırır ve satırları dict listesi olarak döner.

        Args:
            sql: SELECT sorgusu.
            params: Parametreli sorgu için bind değerleri.
            limit: Dönen maksimum satır sayısı (güvenlik sınırı).
        """
        self._validate_read_only(sql)

        engine = self.connect()
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                rows = result.mappings().fetchmany(limit)
                return [dict(row) for row in rows]
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Sorgu çalıştırılamadı: {exc}") from exc


# --- Hızlı test ---
# Çalıştır:  python -m src.connectors.postgres
if __name__ == "__main__":
    import os
    from pathlib import Path

    try:
        from dotenv import load_dotenv

        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
    except ImportError:
        pass  # python-dotenv yoksa ortam değişkenleri doğrudan kullanılır

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL .env dosyasında tanımlı değil; test atlandı.")
    else:
        connector = PostgresConnector(db_url)
        result = connector.test_connection()
        print(result)

        if result["ok"]:
            print("\n=== Şema (prompt formatı) ===")
            try:
                print(connector.schema_to_prompt())
            except RuntimeError as exc:
                print(f"Şema okunamadı: {exc}")
        else:
            print(
                "\nPostgreSQL'e bağlanılamadı. Sunucunun çalıştığından emin olun.\n"
                "Yerel geliştirme için:  docker compose up -d"
            )

        connector.close()
