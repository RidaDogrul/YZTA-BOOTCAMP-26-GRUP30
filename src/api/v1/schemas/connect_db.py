"""Veri kaynağı bağlantı endpoint'leri için request/response modelleri."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConnectDbRequest(BaseModel):
    """PostgreSQL, MySQL, MongoDB, S3 veya Snowflake veri kaynağına bağlanmak için gönderilen istek."""

    source_type: Literal["postgresql", "mysql", "mongodb", "s3", "snowflake"] = Field(
        ...,
        description="Bağlanılacak veri kaynağı türü",
        examples=["postgresql"],
    )
    # --- PostgreSQL / MySQL ---
    connection_url: str | None = Field(
        default=None,
        description="PostgreSQL veya MySQL için SQLAlchemy bağlantı adresi",
        examples=[
            "postgresql+psycopg2://postgres:****@localhost:5432/mydb",
            "mysql+pymysql://root:****@localhost:3306/mydb",
        ],
    )
    # --- MongoDB ---
    mongodb_uri: str | None = Field(
        default=None,
        description="MongoDB bağlantı URI'si",
        examples=["mongodb://localhost:27017/mydb"],
    )
    # --- S3 ---
    bucket_name: str | None = Field(
        default=None,
        description="S3 kaynağı için bucket adı",
        examples=["my-data-bucket"],
    )
    aws_access_key_id: str | None = Field(
        default=None,
        description="AWS erişim anahtarı kimliği",
        examples=["AKIAIOSFODNN7EXAMPLE"],
    )
    aws_secret_access_key: str | None = Field(
        default=None,
        description="AWS gizli erişim anahtarı",
        examples=["wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"],
    )
    aws_region: str | None = Field(
        default="eu-central-1",
        description="AWS bölgesi",
        examples=["eu-central-1"],
    )
    prefix: str | None = Field(
        default=None,
        description="S3 kaynağı için opsiyonel klasör öneki",
        examples=["data/raw/"],
    )
    # --- Snowflake ---
    snowflake_account: str | None = Field(
        default=None,
        description="Snowflake hesap tanımlayıcısı (örn: xy12345.eu-central-1)",
        examples=["xy12345.eu-central-1"],
    )
    snowflake_user: str | None = Field(
        default=None,
        description="Snowflake kullanıcı adı",
        examples=["myuser"],
    )
    snowflake_password: str | None = Field(
        default=None,
        description="Snowflake parolası",
        examples=["mypassword"],
    )
    snowflake_database: str | None = Field(
        default=None,
        description="Snowflake veritabanı adı",
        examples=["MY_DB"],
    )
    snowflake_schema: str | None = Field(
        default="PUBLIC",
        description="Snowflake şema adı",
        examples=["PUBLIC"],
    )
    snowflake_warehouse: str | None = Field(
        default=None,
        description="Snowflake sanal deposu (warehouse)",
        examples=["COMPUTE_WH"],
    )
    snowflake_role: str | None = Field(
        default=None,
        description="Snowflake kullanıcı rolü (opsiyonel)",
        examples=["SYSADMIN"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source_type": "postgresql",
                    "connection_url": "postgresql+psycopg2://postgres:****@localhost:5432/mydb",
                },
                {
                    "source_type": "mysql",
                    "connection_url": "mysql+pymysql://root:****@localhost:3306/mydb",
                },
                {
                    "source_type": "mongodb",
                    "mongodb_uri": "mongodb://localhost:27017/mydb",
                },
                {
                    "source_type": "s3",
                    "bucket_name": "my-data-bucket",
                    "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    "aws_region": "eu-central-1",
                    "prefix": "data/raw/",
                },
                {
                    "source_type": "snowflake",
                    "snowflake_account": "xy12345.eu-central-1",
                    "snowflake_user": "myuser",
                    "snowflake_password": "****",
                    "snowflake_database": "MY_DB",
                    "snowflake_schema": "PUBLIC",
                    "snowflake_warehouse": "COMPUTE_WH",
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
    warehouse: str | None = Field(
        default=None,
        description="Aktif Snowflake warehouse (yalnızca snowflake)",
    )
    snowflake_schema: str | None = Field(
        default=None,
        description="Aktif Snowflake şema adı (yalnızca snowflake)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ok": True,
                    "message": "PostgreSQL bağlantısı başarılı.",
                    "source_type": "postgresql",
                    "version": "PostgreSQL 16.2 on x86_64-linux",
                    "database": None,
                    "bucket": None,
                    "region": None,
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
    files: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Veri dosyaları listesi (s3)",
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
                    "collections": [],
                    "files": [],
                }
            ]
        }
    }


class DisconnectResponse(BaseModel):
    """Oturum kapatma işlemi sonucu."""

    ok: bool = Field(..., description="Oturumun başarıyla kapatılıp kapatılmadığı")
    message: str = Field(..., description="İşlem sonucu mesajı")
    session_id: str = Field(..., description="Kapatılan oturum kimliği")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ok": True,
                    "message": "Oturum başarıyla kapatıldı.",
                    "session_id": "sess_abc123",
                }
            ]
        }
    }


class SessionInfoResponse(BaseModel):
    """Aktif oturum bilgisi."""

    session_id: str = Field(..., description="Oturum kimliği")
    source_type: str = Field(..., description="Bağlı kaynak türü")
    created_at: datetime = Field(..., description="Oturum oluşturulma zamanı")
    last_accessed: datetime = Field(..., description="Son erişim zamanı")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "sess_abc123",
                    "source_type": "postgresql",
                    "created_at": "2026-07-07T10:00:00Z",
                    "last_accessed": "2026-07-07T10:05:00Z",
                }
            ]
        }
    }


class SessionListResponse(BaseModel):
    """Aktif oturum listesi."""

    sessions: list[SessionInfoResponse] = Field(
        ...,
        description="Tüm aktif oturumların listesi",
    )
    total: int = Field(..., description="Toplam aktif oturum sayısı")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sessions": [
                        {
                            "session_id": "sess_abc123",
                            "source_type": "postgresql",
                            "created_at": "2026-07-07T10:00:00Z",
                            "last_accessed": "2026-07-07T10:05:00Z",
                        }
                    ],
                    "total": 1,
                }
            ]
        }
    }
