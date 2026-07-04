"""
Tüm veritabanı konnektörleri için ortak temel sınıf.
postgres.py ve mysql.py'nin PAYLAŞTIĞI mantık burada toplanır; alt sınıflar
yalnızca kendi bağlantı adreslerini (db_url) sağlar.

Böylece bağlan / kapat / test et / şema çıkar / SELECT çalıştır mantığı
tek yerde yazılır, her veritabanında tekrar edilmez.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
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


class BaseDBConfig(BaseModel):
    """Tüm veritabanları için ortak bağlantı parametreleri."""

    host: str = "localhost"
    port: int = Field(..., ge=1, le=65535)  # varsayılan portu alt sınıf verir
    database: str
    user: str
    password: SecretStr

    @field_validator("database", "user")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Alan boş olamaz.")
        return value

    def to_url(self) -> str:
        """SQLAlchemy bağlantı adresi. Her veritabanı kendi şemasını verir."""
        raise NotImplementedError


class BaseConnector(ABC):
    """
    Ortak konnektör mantığı. Alt sınıflar (PostgresConnector, MySQLConnector)
    yalnızca 'db_url' sağlar; gerisi buradan miras alınır.
    """

    # Alt sınıf daha okunaklı mesaj için ezebilir ("PostgreSQL", "MySQL").
    DB_NAME: str = "Veritabanı"

    def __init__(self) -> None:
        self._engine: Engine | None = None

    @property
    @abstractmethod
    def db_url(self) -> str:
        """Alt sınıf kendi bağlantı adresini döndürür."""
        ...

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
        Returns: {"ok": bool, "message": str, "version": str (başarılıysa)}
        'SELECT version()' hem PostgreSQL hem MySQL'de çalışır.
        """
        try:
            engine = self.connect()
            with engine.connect() as conn:
                version = conn.execute(text("SELECT version()")).scalar()
            return {
                "ok": True,
                "message": f"{self.DB_NAME} bağlantısı başarılı.",
                "version": version,
            }
        except SQLAlchemyError as exc:
            return {"ok": False, "message": f"Bağlantı hatası: {exc}"}

    def extract_schema(self) -> dict[str, Any]:
        """Tablo, sütun ve ilişki meta-verisini çıkarır (schema_extractor'a devreder)."""
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
        """Salt-okunur SQL sorgusu çalıştırır, satırları dict listesi olarak döner."""
        self._validate_read_only(sql)
        engine = self.connect()
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                rows = result.mappings().fetchmany(limit)
                return [dict(row) for row in rows]
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Sorgu çalıştırılamadı: {exc}") from exc