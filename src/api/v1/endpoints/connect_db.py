"""
Veri kaynağı bağlantı endpoint'leri.

Desteklenen kaynaklar: PostgreSQL, MySQL, MongoDB, AWS S3, Snowflake

Endpoint'ler:
    POST /connect-db/test          → Bağlantıyı test et (oturum açmadan)
    POST /connect-db/connect       → Oturum aç, session_id döndür
    GET  /connect-db/schema/{sid}  → Aktif oturumun şemasını getir
    DELETE /connect-db/disconnect/{sid} → Oturumu kapat
    GET  /connect-db/sessions      → Tüm aktif oturumları listele (debug)
"""
from typing import cast
from fastapi import APIRouter, HTTPException, status
from pydantic import SecretStr

from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.connect_db import (
    ConnectDbRequest,
    ConnectDbResponse,
    DisconnectResponse,
    SchemaResponse,
    SessionInfoResponse,
    SessionListResponse,
    TestConnectionResponse,
)
from src.connectors.base import BaseConnector
from src.connectors.mongodb import MongoConnector
from src.connectors.mysql import MySQLConnector
from src.connectors.postgres import PostgresConnector
from src.connectors.s3_storage import S3Config, S3Connector
from src.connectors.snowflake_conn import SnowflakeConfig, SnowflakeConnector
from src.utils.logger import get_logger
from src.utils.session_store import session_store

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /test
# ---------------------------------------------------------------------------
@router.post(
    "/test",
    response_model=TestConnectionResponse,
    summary="Veri kaynağı bağlantı testi",
    description=(
        "PostgreSQL, MySQL, MongoDB, S3 veya Snowflake kimlik bilgilerinin geçerli olup olmadığını "
        "kontrol eder. Kalıcı oturum açmadan önce 'Bağlantıyı Test Et' için kullanılır."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Eksik veya geçersiz parametre"},
        500: {"model": ErrorResponse, "description": "Bağlantı testi başarısız"},
    },
)
def test_connection(payload: ConnectDbRequest) -> TestConnectionResponse:
    """
    Örnek (PostgreSQL):
    ```json
    {"source_type": "postgresql",
     "connection_url": "postgresql+psycopg2://user:pass@localhost:5432/mydb"}
    ```
    Örnek (MySQL):
    ```json
    {"source_type": "mysql",
     "connection_url": "mysql+pymysql://user:pass@localhost:3306/mydb"}
    ```
    Örnek (Snowflake):
    ```json
    {"source_type": "snowflake",
     "snowflake_account": "xy12345.eu-central-1",
     "snowflake_user": "myuser",
     "snowflake_password": "mypassword",
     "snowflake_database": "MY_DB",
     "snowflake_schema": "PUBLIC",
     "snowflake_warehouse": "COMPUTE_WH"}
    ```
    Örnek (S3):
    ```json
    {"source_type": "s3",
     "bucket_name": "my-bucket",
     "aws_access_key_id": "AKIA...",
     "aws_secret_access_key": "secret",
     "aws_region": "eu-central-1"}
    ```
    """
    try:
        connector = _build_connector(payload)
        result = connector.test_connection()
    except (ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Bağlantı testi hatası", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bağlantı testi başarısız: {exc}",
        ) from exc

    if not result["ok"]:
        logger.warning("Bağlantı testi başarısız", extra={"source_type": payload.source_type})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"],
        )

    logger.info("Bağlantı testi başarılı", extra={"source_type": payload.source_type})
    return TestConnectionResponse(
        ok=True,
        message=result["message"],
        source_type=payload.source_type,
        version=result.get("version"),
        database=result.get("database"),
        bucket=result.get("bucket"),
        region=result.get("region"),
        warehouse=result.get("warehouse"),
        snowflake_schema=result.get("schema"),
    )


# ---------------------------------------------------------------------------
# POST /connect
# ---------------------------------------------------------------------------
@router.post(
    "/connect",
    response_model=ConnectDbResponse,
    summary="Veri kaynağına bağlan",
    description=(
        "Bağlantıyı doğrular, kalıcı oturum açar ve `session_id` döner. "
        "Frontend bu değeri sonraki chat/reports isteklerinde kullanır."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz bağlantı parametreleri"},
        500: {"model": ErrorResponse, "description": "Bağlantı kurulamadı"},
    },
)
def connect_data_source(payload: ConnectDbRequest) -> ConnectDbResponse:
    try:
        connector = _build_connector(payload)
        result = connector.test_connection()
    except (ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Bağlantı hatası", extra={"source_type": payload.source_type, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bağlantı kurulamadı: {exc}",
        ) from exc

    if not result["ok"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"],
        )

    session_id = session_store.create_session(
        connector=connector,
        source_type=payload.source_type,
    )

    message = _build_connect_message(payload.source_type, result)
    logger.info("Session açıldı", extra={"session_id": session_id, "source_type": payload.source_type})

    return ConnectDbResponse(
        source_type=payload.source_type,
        message=message,
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# GET /schema/{session_id}
# ---------------------------------------------------------------------------
@router.get(
    "/schema/{session_id}",
    response_model=SchemaResponse,
    summary="Bağlı kaynağın şemasını getir",
    description=(
        "Aktif oturumdaki veri kaynağının şema/koleksiyon/dosya meta-verisini döner. "
        "Chat ekranındaki 'Bağlı Kaynak' panelinde ve Text-to-SQL pipeline'ında kullanılır."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı veya süresi doldu"},
        500: {"model": ErrorResponse, "description": "Şema okunamadı"},
    },
)
def get_schema(session_id: str) -> SchemaResponse:
    connector, source_type = _get_active_connector(session_id)

    try:
        if source_type in ("postgresql", "mysql", "snowflake"):
            schema_dict = connector.extract_schema()
            schema_text = connector.schema_to_prompt()
            return SchemaResponse(
                source_type=source_type,
                schema_text=schema_text,
                tables=schema_dict.get("tables", []),
            )

        elif source_type == "mongodb":
            schema_dict = connector.extract_schema()
            schema_text = connector.schema_to_prompt()
            return SchemaResponse(
                source_type=source_type,
                schema_text=schema_text,
                collections=schema_dict.get("collections", []),
            )

        elif source_type == "s3":
            s3: S3Connector = connector  # type: ignore[assignment]
            files = s3.list_data_files(max_keys=100)
            schema_text = _s3_files_to_schema_text(files)
            return SchemaResponse(
                source_type=source_type,
                schema_text=schema_text,
                files=files,
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Bilinmeyen kaynak tipi: {source_type}",
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Şema okuma hatası", extra={"session_id": session_id, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Şema okunamadı: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# DELETE /disconnect/{session_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/disconnect/{session_id}",
    response_model=DisconnectResponse,
    summary="Oturumu kapat",
    description=(
        "Aktif veri kaynağı oturumunu kapatır ve bağlantıyı temizler. "
        "Frontend logout veya 'Bağlantıyı Kes' butonunda kullanılır."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı"},
    },
)
def disconnect(session_id: str) -> DisconnectResponse:
    closed = session_store.close_session(session_id)
    if not closed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturum bulunamadı veya zaten kapatılmış.",
        )

    logger.info("Session kapatıldı", extra={"session_id": session_id})
    return DisconnectResponse(
        ok=True,
        message="Oturum başarıyla kapatıldı.",
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# GET /sessions
# ---------------------------------------------------------------------------
@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="Aktif oturumları listele",
    description=(
        "Sunucudaki tüm aktif veri kaynağı oturumlarını döner. "
        "Yönetim paneli ve debug senaryoları için kullanılır."
    ),
)
def list_sessions() -> SessionListResponse:
    raw = session_store.list_sessions()
    sessions = [
        SessionInfoResponse(
            session_id=s["session_id"],
            source_type=s["source_type"],
            created_at=s["created_at"],
            last_accessed=s["last_accessed"],
        )
        for s in raw
    ]
    return SessionListResponse(sessions=sessions, total=len(sessions))


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------
def _build_connector(payload: ConnectDbRequest) -> BaseConnector:
    """Request payload'undan uygun konnektörü oluşturur."""
    if payload.source_type == "postgresql":
        if not payload.connection_url:
            raise ValueError("PostgreSQL için connection_url zorunludur.")
        return cast(BaseConnector, PostgresConnector(payload.connection_url))

    elif payload.source_type == "mysql":
        if not payload.connection_url:
            raise ValueError("MySQL için connection_url zorunludur.")
        return MySQLConnector(payload.connection_url)

    elif payload.source_type == "mongodb":
        if not payload.mongodb_uri:
            raise ValueError("MongoDB için mongodb_uri zorunludur.")
        return cast(BaseConnector, MongoConnector(payload.mongodb_uri))

    elif payload.source_type == "s3":
        missing = [
            f for f, v in [
                ("bucket_name", payload.bucket_name),
                ("aws_access_key_id", payload.aws_access_key_id),
                ("aws_secret_access_key", payload.aws_secret_access_key),
            ] if not v
        ]
        if missing:
            raise ValueError(f"S3 için zorunlu alanlar eksik: {', '.join(missing)}")

        config = S3Config(
            bucket_name=payload.bucket_name,  # type: ignore[arg-type]
            region=payload.aws_region or "eu-central-1",
            access_key_id=SecretStr(payload.aws_access_key_id),  # type: ignore[arg-type]
            secret_access_key=SecretStr(payload.aws_secret_access_key),  # type: ignore[arg-type]
            prefix=payload.prefix or "",
        )
        return cast(BaseConnector, S3Connector(config))

    elif payload.source_type == "snowflake":
        missing = [
            f for f, v in [
                ("snowflake_account",  payload.snowflake_account),
                ("snowflake_user",     payload.snowflake_user),
                ("snowflake_password", payload.snowflake_password),
                ("snowflake_database", payload.snowflake_database),
            ] if not v
        ]
        if missing:
            raise ValueError(f"Snowflake için zorunlu alanlar eksik: {', '.join(missing)}")

        sf_config = SnowflakeConfig(
            account=payload.snowflake_account,        # type: ignore[arg-type]
            user=payload.snowflake_user,              # type: ignore[arg-type]
            password=SecretStr(payload.snowflake_password),  # type: ignore[arg-type]
            database=payload.snowflake_database,      # type: ignore[arg-type]
            schema_name=payload.snowflake_schema or "PUBLIC",
            warehouse=payload.snowflake_warehouse,
            role=payload.snowflake_role,
        )
        return cast(BaseConnector, SnowflakeConnector(sf_config))

    raise ValueError(f"Desteklenmeyen kaynak tipi: {payload.source_type}")


def _get_active_connector(session_id: str) -> tuple[BaseConnector, str]:
    """
    Session store'dan aktif konnektörü ve kaynak tipini döndürür.
    Bulunamazsa 404 fırlatır.
    """
    connector = session_store.get_connector(session_id)
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturum bulunamadı veya süresi doldu.",
        )
    info = session_store.get_session_info(session_id)
    source_type = info["source_type"] if info else "unknown"
    return connector, source_type


def _build_connect_message(source_type: str, result: dict) -> str:
    """Bağlantı başarısı için kaynak tipine özgü mesaj üretir."""
    if source_type == "postgresql":
        return "PostgreSQL veritabanına bağlandı."
    elif source_type == "mysql":
        return "MySQL veritabanına bağlandı."
    elif source_type == "mongodb":
        db = result.get("database", "veritabanı")
        return f"MongoDB '{db}' veritabanına bağlandı."
    elif source_type == "s3":
        bucket = result.get("bucket", "bucket")
        return f"S3 bucket '{bucket}' bağlandı."
    elif source_type == "snowflake":
        db = result.get("database", "veritabanı")
        wh = result.get("warehouse", "")
        wh_part = f" (warehouse: {wh})" if wh else ""
        return f"Snowflake '{db}' veritabanına bağlandı{wh_part}."
    return f"{source_type} kaynağına bağlandı."


def _s3_files_to_schema_text(files: list[dict]) -> str:
    """S3 dosya listesini LLM prompt formatına çevirir."""
    if not files:
        return "S3 bucket'ında desteklenen veri dosyası bulunamadı."
    lines = ["S3 Veri Dosyaları:"]
    for f in files:
        lines.append(f"  - {f['key']}  ({f['size']} bayt, {f['extension']})")
    return "\n".join(lines)
