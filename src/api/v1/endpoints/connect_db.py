"""
Veri kaynağı bağlantı endpoint'leri — Swagger/OpenAPI şablonu.

FS Notları:
- Kullanıcı ayarlar ekranından PostgreSQL, MongoDB veya S3 bağlantısı kurar.
- Başarılı bağlantı sonrası dönen `session_id` chat ve reports endpoint'lerinde kullanılır.
- Gerçek implementasyon Sprint 2'de konnektör modülleriyle tamamlanacak.
"""
from fastapi import APIRouter, HTTPException, status

from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.connect_db import (
    ConnectDbRequest,
    ConnectDbResponse,
    SchemaResponse,
    TestConnectionResponse,
)

router = APIRouter()


@router.post(
    "/test",
    response_model=TestConnectionResponse,
    summary="Veri kaynağı bağlantı testi",
    description=(
        "PostgreSQL, MongoDB veya S3 kimlik bilgilerinin geçerli olup olmadığını kontrol eder. "
        "Kalıcı oturum açmadan önce frontend'in 'Bağlantıyı Test Et' butonunda kullanılır."
    ),
    response_description="Bağlantı testi sonucu.",
    responses={
        400: {"model": ErrorResponse, "description": "Eksik veya geçersiz parametre"},
        500: {"model": ErrorResponse, "description": "Bağlantı testi sırasında sunucu hatası"},
    },
)
def test_connection(payload: ConnectDbRequest) -> TestConnectionResponse:
    """
    Örnek request:
    ```json
    {
      "source_type": "postgresql",
      "connection_url": "postgresql+psycopg2://postgres:****@localhost:5434/pizza_runner"
    }
    ```
    """
    # TODO(Sprint-2): PostgresConnector / MongoConnector / S3Connector ile gerçek test
    if payload.source_type == "postgresql" and not payload.connection_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PostgreSQL için connection_url zorunludur.",
        )
    if payload.source_type == "mongodb" and not payload.mongodb_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MongoDB için mongodb_uri zorunludur.",
        )
    if payload.source_type == "s3" and not payload.bucket_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="S3 için bucket_name zorunludur.",
        )

    version = None
    database = None
    bucket = None
    region = None

    if payload.source_type == "postgresql":
        version = "PostgreSQL 18.1 (örnek)"
    elif payload.source_type == "mongodb":
        version = "7.0 (örnek)"
        database = "mydb"
    elif payload.source_type == "s3":
        bucket = payload.bucket_name
        region = "eu-central-1"

    return TestConnectionResponse(
        ok=True,
        message="Şablon yanıt — gerçek bağlantı testi Sprint 2'de eklenecek.",
        source_type=payload.source_type,
        version=version,
        database=database,
        bucket=bucket,
        region=region,
    )


@router.post(
    "/connect",
    response_model=ConnectDbResponse,
    summary="Veri kaynağına bağlan",
    description=(
        "Test edilmiş bağlantı bilgileriyle kalıcı oturum açar. "
        "Frontend bu endpoint'ten dönen `session_id` değerini localStorage'da saklar."
    ),
    response_description="Başarılı bağlantı özeti ve oturum kimliği.",
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz bağlantı parametreleri"},
        500: {"model": ErrorResponse, "description": "Bağlantı kurulamadı"},
    },
)
def connect_data_source(payload: ConnectDbRequest) -> ConnectDbResponse:
    """Veri kaynağı oturumu açar ve session_id üretir."""
    # TODO(Sprint-2): Oturum yönetimi + konnektör entegrasyonu
    return ConnectDbResponse(
        source_type=payload.source_type,
        message=f"{payload.source_type} kaynağına bağlandı (şablon yanıt).",
        session_id="sess_template_001",
    )


@router.get(
    "/schema/{session_id}",
    response_model=SchemaResponse,
    summary="Bağlı kaynağın şemasını getir",
    description=(
        "Aktif oturumdaki veritabanının şema/koleksiyon meta-verisini döner. "
        "Chat ekranında 'Bağlı Veri Kaynağı' panelinde gösterilebilir."
    ),
    response_description="LLM ve frontend için yapılandırılmış şema bilgisi.",
    responses={
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı"},
        500: {"model": ErrorResponse, "description": "Şema okunamadı"},
    },
)
def get_schema(session_id: str) -> SchemaResponse:
    """Oturuma bağlı veri kaynağının şema meta-verisini döner."""
    # TODO(Sprint-2): session_id -> PostgresConnector.extract_schema()
    return SchemaResponse(
        source_type="postgresql",
        schema_text="Tablo: customers\n  - id: INTEGER  [PK]\n  - name: TEXT",
        tables=[],
    )
