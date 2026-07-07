"""
Snowflake Konnektörü (Görev S2-M1)
------------------------------------
Snowflake Cloud Data Warehouse'a güvenli bağlantı kurar;
şema keşfi ve salt-okunur (SELECT) sorgu çalıştırma işlemlerini yönetir.

SQLAlchemy dialect: snowflake-sqlalchemy
Kurulum: pip install snowflake-sqlalchemy

Bağlantı adresi formatı:
    snowflake://<user>:<password>@<account>/<database>/<schema>?warehouse=<warehouse>&role=<role>

Referans: https://docs.snowflake.com/en/user-guide/sqlalchemy.html
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

# Yalnızca okuma amaçlı sorgulara izin verilir.
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class SnowflakeConfig(BaseModel):
    """Snowflake bağlantı parametreleri."""

    account: str = Field(
        ...,
        description="Snowflake hesap tanımlayıcısı (örn: xy12345.eu-central-1)",
    )
    user: str = Field(..., description="Snowflake kullanıcı adı")
    password: SecretStr = Field(..., description="Snowflake parolası")
    database: str = Field(..., description="Bağlanılacak veritabanı")
    schema_name: str = Field(
        default="PUBLIC",
        description="Veritabanı şema adı",
    )
    warehouse: str | None = Field(
        default=None,
        description="Sorgu çalıştırılacak sanal depo (warehouse)",
    )
    role: str | None = Field(
        default=None,
        description="Kullanıcı rolü",
    )

    @field_validator("account", "user", "database")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Alan boş olamaz.")
        return value.strip()

    def to_url(self) -> str:
        """SQLAlchemy bağlantı adresini üretir."""
        password = self.password.get_secret_value()
        url = (
            f"snowflake://{self.user}:{password}"
            f"@{self.account}/{self.database}/{self.schema_name}"
        )
        params: list[str] = []
        if self.warehouse:
            params.append(f"warehouse={self.warehouse}")
        if self.role:
            params.append(f"role={self.role}")
        if params:
            url += "?" + "&".join(params)
        return url

    @classmethod
    def from_url(cls, url: str) -> "SnowflakeConfig":
        """
        Snowflake bağlantı URL'sinden config üretir.

        Desteklenen format:
            snowflake://user:pass@account/database/schema?warehouse=WH&role=ROLE
        """
        pattern = (
            r"^snowflake://"
            r"(?P<user>[^:@]+)(?::(?P<password>[^@]*))?@"
            r"(?P<account>[^/]+)/"
            r"(?P<database>[^/?]+)"
            r"(?:/(?P<schema>[^?]+))?"
            r"(?:\?(?P<params>.*))?"
        )
        match = re.match(pattern, url, re.IGNORECASE)
        if not match:
            raise ValueError(
                "Geçersiz Snowflake bağlantı adresi. "
                "Beklenen format: snowflake://user:pass@account/database/schema"
            )
        g = match.groupdict()

        # Query string parametrelerini ayrıştır
        warehouse = None
        role = None
        if g.get("params"):
            for part in g["params"].split("&"):
                if "=" in part:
                    key, val = part.split("=", 1)
                    if key.lower() == "warehouse":
                        warehouse = val
                    elif key.lower() == "role":
                        role = val

        return cls(
            account=g["account"],
            user=g["user"],
            password=SecretStr(g.get("password") or ""),
            database=g["database"],
            schema_name=g.get("schema") or "PUBLIC",
            warehouse=warehouse,
            role=role,
        )


class SnowflakeConnector:
    """Snowflake Cloud Data Warehouse konnektörü."""

    DB_NAME = "Snowflake"

    def __init__(self, config: SnowflakeConfig | str) -> None:
        if isinstance(config, str):
            self.config = SnowflakeConfig.from_url(config)
        else:
            self.config = config
        self._engine: Engine | None = None

    @property
    def db_url(self) -> str:
        return self.config.to_url()

    def connect(self) -> Engine:
        """SQLAlchemy engine'i oluşturur veya mevcut olanı döndürür."""
        if self._engine is None:
            self._engine = create_engine(
                self.db_url,
                pool_pre_ping=True,
                # Snowflake bağlantı havuzu önerileri
                pool_size=5,
                max_overflow=5,
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
        Snowflake'e bağlanılabildiğini ve credentials'ın geçerli olduğunu doğrular.

        Returns:
            {
                "ok": bool,
                "message": str,
                "version": str,       # Snowflake sürümü
                "warehouse": str,     # Aktif warehouse
                "database": str,      # Bağlı veritabanı
                "schema": str,        # Aktif şema
            }
        """
        try:
            engine = self.connect()
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT CURRENT_VERSION(), "
                        "CURRENT_WAREHOUSE(), "
                        "CURRENT_DATABASE(), "
                        "CURRENT_SCHEMA()"
                    )
                ).fetchone()

            return {
                "ok": True,
                "message": "Snowflake bağlantısı başarılı.",
                "version": row[0] if row else None,
                "warehouse": row[1] if row else None,
                "database": row[2] if row else None,
                "schema": row[3] if row else None,
            }
        except SQLAlchemyError as exc:
            return {
                "ok": False,
                "message": f"Bağlantı hatası: {exc}",
            }

    def extract_schema(self) -> dict[str, Any]:
        """
        Snowflake şemasındaki tabloların meta-verisini çıkarır.

        schema_extractor SQLAlchemy Inspector'ı kullandığından
        snowflake-sqlalchemy dialect desteğiyle çalışır.
        """
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
            raise ValueError("Yalnızca okuma (SELECT) sorgularına izin verilir.")
        if not stripped.upper().lstrip().startswith("SELECT"):
            raise ValueError("Sorgu SELECT ile başlamalıdır.")

    def execute_query(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Salt-okunur SQL sorgusu çalıştırır, satırları dict listesi olarak döner.

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


# ---------------------------------------------------------------------------
# Hızlı test
# Çalıştır: python -m src.connectors.snowflake_conn
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    from pathlib import Path

    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
    except ImportError:
        pass

    snowflake_url = os.getenv("SNOWFLAKE_URL")
    if not snowflake_url:
        print("SNOWFLAKE_URL .env dosyasında tanımlı değil; test atlandı.")
    else:
        connector = SnowflakeConnector(snowflake_url)
        result = connector.test_connection()
        print(result)

        if result["ok"]:
            print(f"\nWarehouse : {result['warehouse']}")
            print(f"Database  : {result['database']}")
            print(f"Schema    : {result['schema']}")
            print(f"Version   : {result['version']}")
            print("\n=== Şema (prompt formatı) ===")
            try:
                print(connector.schema_to_prompt())
            except RuntimeError as exc:
                print(f"Şema okunamadı: {exc}")
        connector.close()
