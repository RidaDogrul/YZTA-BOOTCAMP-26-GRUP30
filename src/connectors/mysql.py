"""
MySQL konnektörü. BaseConnector'daki ortak mantığı miras alır; yalnızca
MySQL'e özgü bağlantı adresini (mysql+pymysql://...) sağlar.
postgres.py ile birebir aynı arayüzü paylaşır.
"""
from __future__ import annotations

import re

from pydantic import Field, SecretStr

from src.connectors.base import BaseConnector, BaseDBConfig


class MySQLConfig(BaseDBConfig):
    """MySQL bağlantı parametreleri."""

    port: int = Field(default=3306, ge=1, le=65535)

    def to_url(self) -> str:
        """SQLAlchemy bağlantı adresini üretir (pymysql sürücüsü)."""
        password = self.password.get_secret_value()
        return (
            f"mysql+pymysql://{self.user}:{password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @classmethod
    def from_url(cls, db_url: str) -> "MySQLConfig":
        """Tam URL'den config üretir. Örn: mysql+pymysql://user:pass@host:3306/db"""
        pattern = (
            r"^mysql(?:\+pymysql)?://"
            r"(?P<user>[^:@/]+)(?::(?P<password>[^@]*))?@"
            r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/"
            r"(?P<database>[^?]+)"
        )
        match = re.match(pattern, db_url)
        if not match:
            raise ValueError("Geçersiz MySQL bağlantı adresi.")
        g = match.groupdict()
        return cls(
            host=g["host"],
            port=int(g["port"] or 3306),
            database=g["database"],
            user=g["user"],
            password=SecretStr(g["password"] or ""),
        )


class MySQLConnector(BaseConnector):
    """MySQL veritabanı konnektörü."""

    DB_NAME = "MySQL"

    def __init__(self, config: MySQLConfig | str) -> None:
        super().__init__()
        if isinstance(config, str):
            self.config = MySQLConfig.from_url(config)
        else:
            self.config = config

    @property
    def db_url(self) -> str:
        return self.config.to_url()


# Hızlı test
# Çalıştır: python -m src.connectors.mysql
if __name__ == "__main__":
    import os
    from pathlib import Path

    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
    except ImportError:
        pass

    db_url = os.getenv("MYSQL_URL")
    if not db_url:
        print("MYSQL_URL .env dosyasında tanımlı değil; test atlandı.")
    else:
        connector = MySQLConnector(db_url)
        result = connector.test_connection()
        print(result)
        if result["ok"]:
            print("\n=== Şema (prompt formatı) ===")
            try:
                print(connector.schema_to_prompt())
            except RuntimeError as exc:
                print(f"Şema okunamadı: {exc}")
        connector.close()