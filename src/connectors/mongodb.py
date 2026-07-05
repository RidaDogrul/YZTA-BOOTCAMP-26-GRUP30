"""
MongoDB Konnektörü (Görev 1.1)
--------------------------------
MongoDB veritabanlarına güvenli bağlantı kurar; koleksiyon keşfi,
şema çıkarma ve salt-okunur sorgu işlemlerini yönetir.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator

from bson import ObjectId
from pydantic import BaseModel, Field, SecretStr, field_validator
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

# Yalnızca okuma amaçlı operatörler (güvenlik filtresi).
_FORBIDDEN_QUERY_KEYS = re.compile(
    r"^\$?(where|function|accumulator|merge|out)$",
    re.IGNORECASE,
)


class MongoConfig(BaseModel):
    """MongoDB bağlantı parametreleri."""

    host: str = "localhost"
    port: int = Field(default=27017, ge=1, le=65535)
    database: str
    user: str | None = None
    password: SecretStr | None = None
    auth_source: str = "admin"
    uri: str | None = None

    @field_validator("database")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Veritabanı adı boş olamaz.")
        return value.strip()

    def to_uri(self) -> str:
        """MongoDB bağlantı URI'sini üretir."""
        if self.uri:
            return self.uri

        if self.user and self.password:
            password = self.password.get_secret_value()
            return (
                f"mongodb://{self.user}:{password}"
                f"@{self.host}:{self.port}/{self.database}"
                f"?authSource={self.auth_source}"
            )
        return f"mongodb://{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_uri(cls, uri: str) -> "MongoConfig":
        """
        Tam MongoDB URI'sinden konfigürasyon oluşturur.
        Örnek: mongodb://user:pass@localhost:27017/mydb?authSource=admin
        """
        pattern = (
            r"^mongodb(?:\+srv)?://"
            r"(?:(?P<user>[^:@/]+)(?::(?P<password>[^@]*))?@)?"
            r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/"
            r"(?P<database>[^?]+)"
            r"(?:\?(?P<params>.*))?"
        )
        match = re.match(pattern, uri)
        if not match:
            raise ValueError("Geçersiz MongoDB bağlantı adresi.")

        groups = match.groupdict()
        auth_source = "admin"
        if groups.get("params"):
            for part in groups["params"].split("&"):
                if part.startswith("authSource="):
                    auth_source = part.split("=", 1)[1]

        return cls(
            host=groups["host"] or "localhost",
            port=int(groups["port"] or 27017),
            database=groups["database"],
            user=groups.get("user"),
            password=SecretStr(groups["password"]) if groups.get("password") else None,
            auth_source=auth_source,
            uri=uri,
        )

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "MongoConfig":
        """Ortam değişkenlerinden konfigürasyon oluşturur."""
        uri = env.get("MONGODB_URI")
        if uri:
            return cls.from_uri(uri)

        database = env.get("MONGODB_DATABASE")
        if not database:
            raise ValueError("MONGODB_URI veya MONGODB_DATABASE ortam değişkeni zorunludur.")

        password = env.get("MONGODB_PASSWORD")
        return cls(
            host=env.get("MONGODB_HOST", "localhost"),
            port=int(env.get("MONGODB_PORT", "27017")),
            database=database,
            user=env.get("MONGODB_USER"),
            password=SecretStr(password) if password else None,
            auth_source=env.get("MONGODB_AUTH_SOURCE", "admin"),
        )


class MongoConnector:
    """MongoDB veritabanı konnektörü."""

    def __init__(self, config: MongoConfig | str) -> None:
        if isinstance(config, str):
            self.config = MongoConfig.from_uri(config)
        else:
            self.config = config
        self._client: MongoClient | None = None

    def connect(self) -> MongoClient:
        """MongoDB istemcisini oluşturur veya mevcut olanı döndürür."""
        if self._client is None:
            self._client = MongoClient(
                self.config.to_uri(),
                serverSelectionTimeoutMS=5000,
            )
        return self._client

    def close(self) -> None:
        """Açık bağlantıları kapatır."""
        if self._client is not None:
            self._client.close()
            self._client = None

    @contextmanager
    def session(self) -> Generator[MongoClient, None, None]:
        """Bağlantıyı otomatik kapatacak context manager."""
        client = self.connect()
        try:
            yield client
        finally:
            self.close()

    def _get_database(self) -> Database:
        client = self.connect()
        return client[self.config.database]

    def test_connection(self) -> dict[str, Any]:
        """
        Veritabanına bağlanılabildiğini doğrular.

        Returns:
            {"ok": True/False, "message": "...", "version": "..." (başarılıysa)}
        """
        try:
            client = self.connect()
            server_info = client.server_info()
            return {
                "ok": True,
                "message": "MongoDB bağlantısı başarılı.",
                "version": server_info.get("version"),
                "database": self.config.database,
            }
        except PyMongoError as exc:
            return {
                "ok": False,
                "message": f"Bağlantı hatası: {exc}",
            }

    def list_collections(self) -> list[str]:
        """Veritabanındaki koleksiyon adlarını döner."""
        try:
            return sorted(self._get_database().list_collection_names())
        except PyMongoError as exc:
            raise RuntimeError(f"Koleksiyonlar listelenemedi: {exc}") from exc

    def extract_schema(self, sample_size: int = 5) -> dict[str, Any]:
        """
        Koleksiyonlardan örnek belgeler alarak alan şemasını çıkarır.

        Returns:
            {"collections": [{"collection_name", "fields": [...]}]}
        """
        try:
            db = self._get_database()
            collections: list[dict[str, Any]] = []

            for name in sorted(db.list_collection_names()):
                samples = list(db[name].find().limit(sample_size))
                fields = _infer_fields_from_samples(samples)
                collections.append(
                    {
                        "collection_name": name,
                        "fields": fields,
                        "sample_count": len(samples),
                    }
                )

            return {"collections": collections}
        except PyMongoError as exc:
            raise RuntimeError(f"Şema çıkarılamadı: {exc}") from exc

    def schema_to_prompt(self, sample_size: int = 5) -> str:
        """LLM prompt'u için okunaklı şema metni üretir."""
        return _schema_to_prompt_string(self.extract_schema(sample_size))

    @staticmethod
    def _validate_read_only_filter(filter_query: dict[str, Any] | None) -> None:
        """Yalnızca güvenli okuma filtrelerine izin verir."""
        if not filter_query:
            return

        for key in filter_query:
            if _FORBIDDEN_QUERY_KEYS.match(str(key)):
                raise ValueError(f"Güvenli olmayan sorgu operatörü: {key}")

    def find_documents(
        self,
        collection: str,
        filter_query: dict[str, Any] | None = None,
        limit: int = 100,
        projection: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Salt-okunur find sorgusu çalıştırır.

        Args:
            collection: Koleksiyon adı.
            filter_query: MongoDB find filtresi.
            limit: Dönen maksimum belge sayısı.
            projection: Döndürülecek alanlar.
        """
        self._validate_read_only_filter(filter_query)

        try:
            coll: Collection = self._get_database()[collection]
            cursor = coll.find(filter_query or {}, projection).limit(limit)
            return [_serialize_document(doc) for doc in cursor]
        except PyMongoError as exc:
            raise RuntimeError(f"Sorgu çalıştırılamadı: {exc}") from exc


def _infer_type(value: Any) -> str:
    """Python değerinden MongoDB alan tipi çıkarır."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "string"
    if isinstance(value, ObjectId):
        return "ObjectId"
    if isinstance(value, datetime):
        return "datetime"
    if isinstance(value, list):
        inner = _infer_type(value[0]) if value else "mixed"
        return f"array<{inner}>"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _merge_field_types(existing: str, new: str) -> str:
    """Aynı alan için farklı tipleri birleştirir."""
    if existing == new:
        return existing
    return f"{existing}|{new}"


def _infer_fields_from_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Örnek belgelerden alan adı ve tip listesi çıkarır (iç içe alanlar dahil)."""
    field_types: dict[str, str] = {}

    def walk(prefix: str, value: Any) -> None:
        inferred = _infer_type(value)
        if prefix in field_types:
            field_types[prefix] = _merge_field_types(field_types[prefix], inferred)
        else:
            field_types[prefix] = inferred

        if isinstance(value, dict):
            for key, nested in value.items():
                walk(f"{prefix}.{key}" if prefix else key, nested)

    for doc in samples:
        for key, value in doc.items():
            walk(key, value)

    return [
        {"name": name, "type": field_types[name]}
        for name in sorted(field_types)
    ]


def _serialize_document(doc: dict[str, Any]) -> dict[str, Any]:
    """ObjectId ve datetime değerlerini JSON uyumlu hale getirir."""
    result: dict[str, Any] = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _serialize_document(value)
        elif isinstance(value, list):
            result[key] = [
                _serialize_document(item) if isinstance(item, dict)
                else str(item) if isinstance(item, ObjectId)
                else item.isoformat() if isinstance(item, datetime)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def _schema_to_prompt_string(schema: dict[str, Any]) -> str:
    """extract_schema çıktısını LLM prompt formatına çevirir."""
    lines: list[str] = []

    for collection in schema["collections"]:
        lines.append(f"Koleksiyon: {collection['collection_name']}")
        for field in collection["fields"]:
            lines.append(f"  - {field['name']}: {field['type']}")
        lines.append("")

    return "\n".join(lines).strip()


# --- Hızlı test ---
# Çalıştır:  python -m src.connectors.mongodb
if __name__ == "__main__":
    import os
    from pathlib import Path

    try:
        from dotenv import load_dotenv

        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
    except ImportError:
        pass

    try:
        config = MongoConfig.from_env(dict(os.environ))
    except ValueError as exc:
        print(f"MongoDB yapılandırması eksik: {exc}")
    else:
        connector = MongoConnector(config)
        result = connector.test_connection()
        print(result)

        if result["ok"]:
            print("\n=== Koleksiyonlar ===")
            try:
                print(connector.list_collections())
            except RuntimeError as exc:
                print(f"Koleksiyonlar listelenemedi: {exc}")
            print("\n=== Şema (prompt formatı) ===")
            try:
                print(connector.schema_to_prompt())
            except RuntimeError as exc:
                print(f"Şema okunamadı: {exc}")
        else:
            print(
                "\nMongoDB'ye bağlanılamadı. Sunucunun çalıştığından emin olun.\n"
                "Yerel geliştirme için:  docker compose up -d mongo"
            )

        connector.close()
