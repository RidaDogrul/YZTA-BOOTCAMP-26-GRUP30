"""
AWS S3 Konnektörü (Görev 1.1)
------------------------------
S3 bucket'larına güvenli bağlantı kurar; dosya listeleme ve
salt-okunur indirme işlemlerini yönetir.
"""
from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Any, Generator

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, SecretStr, field_validator

# Veri analizi için desteklenen dosya uzantıları
_DATA_EXTENSIONS = {".csv", ".json", ".jsonl", ".parquet", ".xlsx", ".xls", ".tsv"}


class S3Config(BaseModel):
    """AWS S3 bağlantı parametreleri."""

    bucket_name: str
    region: str = "eu-central-1"
    access_key_id: SecretStr
    secret_access_key: SecretStr
    prefix: str = ""
    endpoint_url: str | None = None

    @field_validator("bucket_name")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Bucket adı boş olamaz.")
        return value.strip()

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "S3Config":
        """Ortam değişkenlerinden konfigürasyon oluşturur."""
        bucket = env.get("AWS_S3_BUCKET")
        access_key = env.get("AWS_ACCESS_KEY_ID")
        secret_key = env.get("AWS_SECRET_ACCESS_KEY")

        if not bucket or not access_key or not secret_key:
            raise ValueError(
                "AWS_S3_BUCKET, AWS_ACCESS_KEY_ID ve AWS_SECRET_ACCESS_KEY "
                "ortam değişkenleri zorunludur."
            )

        return cls(
            bucket_name=bucket,
            region=env.get("AWS_REGION", "eu-central-1"),
            access_key_id=SecretStr(access_key),
            secret_access_key=SecretStr(secret_key),
            prefix=env.get("AWS_S3_PREFIX", ""),
            endpoint_url=env.get("AWS_ENDPOINT_URL") or None,
        )


class S3Connector:
    """AWS S3 depolama konnektörü."""

    def __init__(self, config: S3Config) -> None:
        self.config = config
        self._client: BaseClient | None = None

    def connect(self) -> BaseClient:
        """S3 istemcisini oluşturur veya mevcut olanı döndürür."""
        if self._client is None:
            session_kwargs: dict[str, Any] = {
                "aws_access_key_id": self.config.access_key_id.get_secret_value(),
                "aws_secret_access_key": self.config.secret_access_key.get_secret_value(),
                "region_name": self.config.region,
            }
            session = boto3.Session(**session_kwargs)
            client_kwargs: dict[str, Any] = {}
            if self.config.endpoint_url:
                client_kwargs["endpoint_url"] = self.config.endpoint_url
            self._client = session.client("s3", **client_kwargs)
        return self._client

    def close(self) -> None:
        """İstemci referansını serbest bırakır."""
        self._client = None

    @contextmanager
    def session(self) -> Generator[BaseClient, None, None]:
        """Bağlantıyı otomatik kapatacak context manager."""
        client = self.connect()
        try:
            yield client
        finally:
            self.close()

    def test_connection(self) -> dict[str, Any]:
        """
        Bucket'a erişilebildiğini doğrular.

        Returns:
            {"ok": True/False, "message": "...", "bucket": "...", "region": "..."}
        """
        try:
            client = self.connect()
            client.head_bucket(Bucket=self.config.bucket_name)
            return {
                "ok": True,
                "message": "S3 bağlantısı başarılı.",
                "bucket": self.config.bucket_name,
                "region": self.config.region,
            }
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            return {
                "ok": False,
                "message": f"S3 bağlantı hatası ({code}): {exc}",
            }
        except BotoCoreError as exc:
            return {
                "ok": False,
                "message": f"S3 bağlantı hatası: {exc}",
            }

    def list_objects(
        self,
        prefix: str | None = None,
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Bucket içindeki nesneleri listeler.

        Args:
            prefix: Alt klasör filtresi; None ise config.prefix kullanılır.
            max_keys: Dönen maksimum nesne sayısı.
        """
        effective_prefix = prefix if prefix is not None else self.config.prefix
        client = self.connect()

        try:
            paginator = client.get_paginator("list_objects_v2")
            objects: list[dict[str, Any]] = []

            for page in paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=effective_prefix,
                PaginationConfig={"MaxItems": max_keys},
            ):
                for obj in page.get("Contents", []):
                    key: str = obj["Key"]
                    objects.append(
                        {
                            "key": key,
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "extension": _get_extension(key),
                        }
                    )
            return objects
        except (ClientError, BotoCoreError) as exc:
            raise RuntimeError(f"Nesneler listelenemedi: {exc}") from exc

    def list_data_files(
        self,
        prefix: str | None = None,
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """Yalnızca desteklenen veri dosyalarını (.csv, .json, .parquet vb.) listeler."""
        return [
            obj
            for obj in self.list_objects(prefix=prefix, max_keys=max_keys)
            if obj["extension"] in _DATA_EXTENSIONS
        ]

    def download_bytes(self, key: str, max_size_mb: int = 50) -> bytes:
        """
        Nesneyi bayt dizisi olarak indirir.

        Args:
            key: S3 nesne anahtarı.
            max_size_mb: İndirilebilecek maksimum dosya boyutu (MB).
        """
        client = self.connect()
        max_bytes = max_size_mb * 1024 * 1024

        try:
            head = client.head_object(Bucket=self.config.bucket_name, Key=key)
            size = head.get("ContentLength", 0)
            if size > max_bytes:
                raise ValueError(
                    f"Dosya çok büyük ({size} bayt). "
                    f"Maksimum: {max_size_mb} MB."
                )

            buffer = io.BytesIO()
            client.download_fileobj(self.config.bucket_name, key, buffer)
            return buffer.getvalue()
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            raise RuntimeError(f"Dosya indirilemedi ({code}): {exc}") from exc
        except BotoCoreError as exc:
            raise RuntimeError(f"Dosya indirilemedi: {exc}") from exc

    def download_text(
        self,
        key: str,
        encoding: str = "utf-8",
        max_size_mb: int = 50,
    ) -> str:
        """Metin dosyasını indirir ve string olarak döner."""
        return self.download_bytes(key, max_size_mb=max_size_mb).decode(encoding)

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        """Nesne meta-verisini döner (boyut, içerik tipi, son değişiklik)."""
        client = self.connect()
        try:
            response = client.head_object(Bucket=self.config.bucket_name, Key=key)
            return {
                "key": key,
                "size": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified", "").isoformat()
                if response.get("LastModified")
                else None,
                "extension": _get_extension(key),
            }
        except (ClientError, BotoCoreError) as exc:
            raise RuntimeError(f"Meta-veri okunamadı: {exc}") from exc


def _get_extension(key: str) -> str:
    """Dosya uzantısını küçük harfle döner."""
    dot = key.rfind(".")
    if dot == -1:
        return ""
    return key[dot:].lower()


# --- Hızlı test ---
# Çalıştır:  python -m src.connectors.s3_storage
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
        config = S3Config.from_env(dict(os.environ))
    except ValueError as exc:
        print(f"S3 yapılandırması eksik: {exc}")
    else:
        connector = S3Connector(config)
        result = connector.test_connection()
        print(result)

        if result["ok"]:
            print("\n=== Veri dosyaları ===")
            try:
                files = connector.list_data_files(max_keys=20)
                if files:
                    for f in files:
                        print(f"  {f['key']}  ({f['size']} bayt)")
                else:
                    print("  (desteklenen veri dosyası bulunamadı)")
            except RuntimeError as exc:
                print(f"Dosyalar listelenemedi: {exc}")

        connector.close()
