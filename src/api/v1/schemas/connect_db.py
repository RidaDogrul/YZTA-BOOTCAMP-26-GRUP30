"""Veri kaynağı bağlantı endpoint'leri için request/response modelleri."""
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConnectDbRequest(BaseModel):
    """PostgreSQL, MongoDB veya S3 veri kaynağına bağlanmak için gönderilen istek."""

    source_type: Literal["postgresql", "mongodb", "s3"] = Field(
        ...,
        description="Bağlanılacak veri kaynağı türü",
        examples=["postgresql"],
    )
    connection_url: str | None = Field(
        default=None,
        description="PostgreSQL için SQLAlchemy bağlantı adresi",
        examples=["postgresql+psycopg2://postgres:****@localhost:5434/pizza_runner"],
    )
    mongodb_uri: str | None = Field(
        default=None,
        description="MongoDB bağlantı URI'si",
        examples=["mongodb://localhost:27017/mydb"],
    )
    bucket_name: str | None = Field(
        default=None,
        description="S3 kaynağı için bucket adı",
        examples=["elifs-macaroon-market"],
    )
    prefix: str | None = Field(
        default=None,
        description="S3 kaynağı için opsiyonel klasör öneki",
        examples=["data/raw/"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source_type": "postgresql",
                    "connection_url": "postgresql+psycopg2://postgres:****@localhost:5434/pizza_runner",
                },
                {
                    "source_type": "mongodb",
                    "mongodb_uri": "mongodb://localhost:27017/mydb",
                },
                {
                    "source_type": "s3",
                    "bucket_name": "elifs-macaroon-market",
                    "prefix": "",
                },
            ]
        }
    }


class TestConnectionResponse(BaseModel):
    """Bağlantı testi sonucu."""

    ok: bool = Field(..., description="Bağlantının başarılı olup olmadığı")
    message: str = Field(..., description="Bağlantı durumu açıklaması")
    source_type: str = Field(..., description="Test edilen kaynak türü")
    version: str | None = Field(
        default=None,
        description="Veritabanı sürüm bilgisi (postgresql / mongodb)",
    )
    database: str | None = Field(
        default=None,
        description="Bağlanılan veritabanı adı (mongodb)",
    )
    bucket: str | None = Field(
        default=None,
        description="Erişilen bucket adı (yalnızca s3)",
    )
    region: str | None = Field(
        default=None,
        description="AWS bölgesi (yalnızca s3)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ok": True,
                    "message": "PostgreSQL bağlantısı başarılı.",
                    "source_type": "postgresql",
                    "version": "PostgreSQL 18.1 on x86_64-windows",
                    "bucket": None,
                    "region": None,
                }
            ]
        }
    }


class SchemaResponse(BaseModel):
    """Veritabanı şema keşif sonucu."""

    source_type: str = Field(..., description="Şema çıkarılan kaynak türü")
    schema_text: str = Field(
        ...,
        description="LLM prompt'una gömülecek okunaklı şema metni",
    )
    tables: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tablo, sütun ve ilişki meta-verisi (postgresql)",
    )
    collections: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Koleksiyon ve alan meta-verisi (mongodb)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source_type": "postgresql",
                    "schema_text": "Tablo: customers\n  - id: INTEGER  [PK]\n  - name: TEXT",
                    "tables": [
                        {
                            "table_name": "customers",
                            "columns": [
                                {"name": "id", "type": "INTEGER", "primary_key": True}
                            ],
                            "foreign_keys": [],
                        }
                    ],
                }
            ]
        }
    }


class ConnectDbResponse(BaseModel):
    """Başarılı veri kaynağı bağlantısı sonrası dönen özet bilgi."""

    status: Literal["connected"] = Field(
        default="connected",
        description="Bağlantı durumu",
    )
    source_type: str = Field(..., description="Bağlanılan kaynak türü")
    message: str = Field(..., description="Bağlantı özeti")
    session_id: str = Field(
        ...,
        description="Frontend'in sonraki isteklerde kullanacağı oturum kimliği",
        examples=["sess_abc123"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "connected",
                    "source_type": "postgresql",
                    "message": "pizza_runner veritabanına bağlandı.",
                    "session_id": "sess_abc123",
                }
            ]
        }
    }
