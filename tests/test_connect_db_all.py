"""
AWS S3, MongoDB ve PostgreSQL connect_db endpoint testleri.

Mock tabanlı unit testler — gerçek sunucu gerektirmez.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.utils.session_store import session_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Her testten önce/sonra session store'u temizle."""
    session_store.clear_all()
    yield
    session_store.clear_all()


# ===========================================================================
# AWS S3
# ===========================================================================

class TestS3ConnectionTest:
    """POST /connect-db/test — S3"""

    @patch("src.api.v1.endpoints.connect_db.S3Connector")
    @patch("src.api.v1.endpoints.connect_db.S3Config")
    def test_successful(self, mock_s3_config, mock_s3_connector):
        """S3 bağlantı testi başarılı."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "S3 bağlantısı başarılı.",
            "bucket": "my-data-bucket",
            "region": "eu-central-1",
        }
        mock_s3_connector.return_value = mock_instance
        mock_s3_config.return_value = MagicMock()

        payload = {
            "source_type": "s3",
            "bucket_name": "my-data-bucket",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "aws_region": "eu-central-1",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["source_type"] == "s3"
        assert data["bucket"] == "my-data-bucket"
        assert data["region"] == "eu-central-1"

    @patch("src.api.v1.endpoints.connect_db.S3Connector")
    @patch("src.api.v1.endpoints.connect_db.S3Config")
    def test_access_denied(self, mock_s3_config, mock_s3_connector):
        """S3 erişim reddi durumu."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": False,
            "message": "S3 bağlantı hatası (403): Access Denied",
        }
        mock_s3_connector.return_value = mock_instance
        mock_s3_config.return_value = MagicMock()

        payload = {
            "source_type": "s3",
            "bucket_name": "my-data-bucket",
            "aws_access_key_id": "WRONG_KEY",
            "aws_secret_access_key": "WRONG_SECRET",
            "aws_region": "eu-central-1",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 500
        assert "Access Denied" in response.json()["detail"]

    def test_missing_bucket_name(self):
        """bucket_name eksikse 400 hatası."""
        payload = {
            "source_type": "s3",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "bucket_name" in response.json()["detail"]

    def test_missing_access_key(self):
        """aws_access_key_id eksikse 400 hatası."""
        payload = {
            "source_type": "s3",
            "bucket_name": "my-data-bucket",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "aws_access_key_id" in response.json()["detail"]


class TestS3Connect:
    """POST /connect-db/connect — S3"""

    @patch("src.api.v1.endpoints.connect_db.S3Connector")
    @patch("src.api.v1.endpoints.connect_db.S3Config")
    def test_successful_connect(self, mock_s3_config, mock_s3_connector):
        """S3 bağlantısı oturum açar ve session_id döner."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "S3 bağlantısı başarılı.",
            "bucket": "my-data-bucket",
            "region": "eu-central-1",
        }
        mock_s3_connector.return_value = mock_instance
        mock_s3_config.return_value = MagicMock()

        payload = {
            "source_type": "s3",
            "bucket_name": "my-data-bucket",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "aws_region": "eu-central-1",
        }
        response = client.post("/api/v1/connect-db/connect", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["source_type"] == "s3"
        assert "my-data-bucket" in data["message"]
        assert data["session_id"].startswith("sess_")

        info = session_store.get_session_info(data["session_id"])
        assert info is not None
        assert info["source_type"] == "s3"


class TestS3Schema:
    """GET /connect-db/schema/{session_id} — S3"""

    @patch("src.api.v1.endpoints.connect_db.S3Connector")
    @patch("src.api.v1.endpoints.connect_db.S3Config")
    def test_get_schema_lists_files(self, mock_s3_config, mock_s3_connector):
        """S3 şeması dosya listesi döner."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "S3 bağlantısı başarılı.",
            "bucket": "my-data-bucket",
            "region": "eu-central-1",
        }
        mock_instance.list_data_files.return_value = [
            {"key": "data/sales.csv",    "size": 1024, "extension": ".csv"},
            {"key": "data/orders.json",  "size": 2048, "extension": ".json"},
            {"key": "data/products.parquet", "size": 4096, "extension": ".parquet"},
        ]
        mock_s3_connector.return_value = mock_instance
        mock_s3_config.return_value = MagicMock()

        # Connect
        payload = {
            "source_type": "s3",
            "bucket_name": "my-data-bucket",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "aws_region": "eu-central-1",
        }
        connect_resp = client.post("/api/v1/connect-db/connect", json=payload)
        session_id = connect_resp.json()["session_id"]

        # Schema
        schema_resp = client.get(f"/api/v1/connect-db/schema/{session_id}")
        assert schema_resp.status_code == 200
        data = schema_resp.json()
        assert data["source_type"] == "s3"
        assert len(data["files"]) == 3
        assert any(f["key"] == "data/sales.csv" for f in data["files"])
        assert "S3 Veri Dosyaları" in data["schema_text"]

    @patch("src.api.v1.endpoints.connect_db.S3Connector")
    @patch("src.api.v1.endpoints.connect_db.S3Config")
    def test_schema_empty_bucket(self, mock_s3_config, mock_s3_connector):
        """Boş bucket için uyarı metni döner."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "S3 bağlantısı başarılı.",
            "bucket": "empty-bucket",
            "region": "eu-central-1",
        }
        mock_instance.list_data_files.return_value = []
        mock_s3_connector.return_value = mock_instance
        mock_s3_config.return_value = MagicMock()

        payload = {
            "source_type": "s3",
            "bucket_name": "empty-bucket",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "aws_region": "eu-central-1",
        }
        connect_resp = client.post("/api/v1/connect-db/connect", json=payload)
        session_id = connect_resp.json()["session_id"]

        schema_resp = client.get(f"/api/v1/connect-db/schema/{session_id}")
        assert schema_resp.status_code == 200
        data = schema_resp.json()
        assert data["files"] == []
        assert "bulunamadı" in data["schema_text"]


# ===========================================================================
# MongoDB
# ===========================================================================

class TestMongoDBConnectionTest:
    """POST /connect-db/test — MongoDB"""

    @patch("src.api.v1.endpoints.connect_db.MongoConnector")
    def test_successful(self, mock_connector_class):
        """MongoDB bağlantı testi başarılı."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "MongoDB bağlantısı başarılı.",
            "version": "7.0.4",
            "database": "mydb",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "mongodb",
            "mongodb_uri": "mongodb://localhost:27017/mydb",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["source_type"] == "mongodb"
        assert data["version"] == "7.0.4"
        assert data["database"] == "mydb"
        mock_connector_class.assert_called_once_with(payload["mongodb_uri"])

    @patch("src.api.v1.endpoints.connect_db.MongoConnector")
    def test_auth_failure(self, mock_connector_class):
        """MongoDB kimlik doğrulama hatası."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": False,
            "message": "Bağlantı hatası: Authentication failed.",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "mongodb",
            "mongodb_uri": "mongodb://wronguser:wrongpass@localhost:27017/mydb",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 500
        assert "Authentication failed" in response.json()["detail"]

    def test_missing_mongodb_uri(self):
        """mongodb_uri eksikse 400 hatası."""
        payload = {"source_type": "mongodb"}
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "mongodb_uri zorunludur" in response.json()["detail"]


class TestMongoDBConnect:
    """POST /connect-db/connect — MongoDB"""

    @patch("src.api.v1.endpoints.connect_db.MongoConnector")
    def test_successful_connect(self, mock_connector_class):
        """MongoDB oturum açma ve session_id dönüşü."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "MongoDB bağlantısı başarılı.",
            "version": "7.0.4",
            "database": "mydb",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "mongodb",
            "mongodb_uri": "mongodb://localhost:27017/mydb",
        }
        response = client.post("/api/v1/connect-db/connect", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["source_type"] == "mongodb"
        assert "mydb" in data["message"]
        assert data["session_id"].startswith("sess_")

        info = session_store.get_session_info(data["session_id"])
        assert info["source_type"] == "mongodb"


class TestMongoDBSchema:
    """GET /connect-db/schema/{session_id} — MongoDB"""

    @patch("src.api.v1.endpoints.connect_db.MongoConnector")
    def test_get_schema_with_collections(self, mock_connector_class):
        """MongoDB şeması koleksiyon listesi döner."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "MongoDB bağlantısı başarılı.",
            "database": "mydb",
        }
        mock_instance.extract_schema.return_value = {
            "collections": [
                {
                    "collection_name": "users",
                    "fields": [
                        {"name": "_id",   "type": "ObjectId"},
                        {"name": "name",  "type": "string"},
                        {"name": "email", "type": "string"},
                    ],
                    "sample_count": 5,
                },
                {
                    "collection_name": "orders",
                    "fields": [
                        {"name": "_id",    "type": "ObjectId"},
                        {"name": "total",  "type": "double"},
                        {"name": "status", "type": "string"},
                    ],
                    "sample_count": 5,
                },
            ]
        }
        mock_instance.schema_to_prompt.return_value = (
            "Koleksiyon: users\n  - _id: ObjectId\n  - email: string\n\n"
            "Koleksiyon: orders\n  - _id: ObjectId\n  - total: double"
        )
        mock_connector_class.return_value = mock_instance

        connect_resp = client.post(
            "/api/v1/connect-db/connect",
            json={"source_type": "mongodb", "mongodb_uri": "mongodb://localhost:27017/mydb"},
        )
        session_id = connect_resp.json()["session_id"]

        schema_resp = client.get(f"/api/v1/connect-db/schema/{session_id}")
        assert schema_resp.status_code == 200
        data = schema_resp.json()
        assert data["source_type"] == "mongodb"
        assert len(data["collections"]) == 2
        collection_names = [c["collection_name"] for c in data["collections"]]
        assert "users" in collection_names
        assert "orders" in collection_names
        assert "Koleksiyon" in data["schema_text"]

    def test_invalid_session(self):
        """Geçersiz session_id ile 404."""
        response = client.get("/api/v1/connect-db/schema/nonexistent_session")
        assert response.status_code == 404


# ===========================================================================
# PostgreSQL
# ===========================================================================

class TestPostgreSQLConnectionTest:
    """POST /connect-db/test — PostgreSQL"""

    @patch("src.api.v1.endpoints.connect_db.PostgresConnector")
    def test_successful(self, mock_connector_class):
        """PostgreSQL bağlantı testi başarılı."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "PostgreSQL bağlantısı başarılı.",
            "version": "PostgreSQL 16.2 on x86_64-linux",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "postgresql",
            "connection_url": "postgresql+psycopg2://postgres:3456@localhost:5432/pizza_runner",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["source_type"] == "postgresql"
        assert "PostgreSQL 16" in data["version"]
        mock_connector_class.assert_called_once_with(payload["connection_url"])

    @patch("src.api.v1.endpoints.connect_db.PostgresConnector")
    def test_wrong_password(self, mock_connector_class):
        """Yanlış şifre durumu."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": False,
            "message": "Bağlantı hatası: password authentication failed for user 'postgres'",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "postgresql",
            "connection_url": "postgresql+psycopg2://postgres:WRONG@localhost:5432/pizza_runner",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 500
        assert "password authentication failed" in response.json()["detail"]

    def test_missing_connection_url(self):
        """connection_url eksikse 400 hatası."""
        payload = {"source_type": "postgresql"}
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "connection_url zorunludur" in response.json()["detail"]


class TestPostgreSQLConnect:
    """POST /connect-db/connect — PostgreSQL"""

    @patch("src.api.v1.endpoints.connect_db.PostgresConnector")
    def test_successful_connect(self, mock_connector_class):
        """PostgreSQL oturum açma ve session_id dönüşü."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "PostgreSQL bağlantısı başarılı.",
            "version": "PostgreSQL 16.2 on x86_64-linux",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "postgresql",
            "connection_url": "postgresql+psycopg2://postgres:3456@localhost:5432/pizza_runner",
        }
        response = client.post("/api/v1/connect-db/connect", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["source_type"] == "postgresql"
        assert "PostgreSQL" in data["message"]
        assert data["session_id"].startswith("sess_")

        info = session_store.get_session_info(data["session_id"])
        assert info["source_type"] == "postgresql"

    @patch("src.api.v1.endpoints.connect_db.PostgresConnector")
    def test_connect_creates_unique_sessions(self, mock_connector_class):
        """Her connect isteği benzersiz session_id üretir."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "PostgreSQL bağlantısı başarılı.",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "postgresql",
            "connection_url": "postgresql+psycopg2://postgres:3456@localhost:5432/pizza_runner",
        }
        r1 = client.post("/api/v1/connect-db/connect", json=payload)
        r2 = client.post("/api/v1/connect-db/connect", json=payload)

        assert r1.json()["session_id"] != r2.json()["session_id"]


class TestPostgreSQLSchema:
    """GET /connect-db/schema/{session_id} — PostgreSQL"""

    @patch("src.api.v1.endpoints.connect_db.PostgresConnector")
    def test_get_schema_with_tables(self, mock_connector_class):
        """PostgreSQL şeması tablo listesi döner."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "PostgreSQL bağlantısı başarılı.",
        }
        mock_instance.extract_schema.return_value = {
            "tables": [
                {
                    "table_name": "customers",
                    "columns": [
                        {"name": "id",   "type": "INTEGER", "primary_key": True},
                        {"name": "name", "type": "TEXT",    "primary_key": False},
                    ],
                    "foreign_keys": [],
                },
                {
                    "table_name": "orders",
                    "columns": [
                        {"name": "id",          "type": "INTEGER", "primary_key": True},
                        {"name": "customer_id", "type": "INTEGER", "primary_key": False},
                        {"name": "total",       "type": "NUMERIC", "primary_key": False},
                    ],
                    "foreign_keys": [
                        {"column": "customer_id", "ref_table": "customers", "ref_column": "id"}
                    ],
                },
            ]
        }
        mock_instance.schema_to_prompt.return_value = (
            "Tablo: customers\n  - id: INTEGER [PK]\n  - name: TEXT\n\n"
            "Tablo: orders\n  - id: INTEGER [PK]\n  - customer_id: INTEGER\n  - total: NUMERIC"
        )
        mock_connector_class.return_value = mock_instance

        connect_resp = client.post(
            "/api/v1/connect-db/connect",
            json={
                "source_type": "postgresql",
                "connection_url": "postgresql+psycopg2://postgres:3456@localhost:5432/pizza_runner",
            },
        )
        session_id = connect_resp.json()["session_id"]

        schema_resp = client.get(f"/api/v1/connect-db/schema/{session_id}")
        assert schema_resp.status_code == 200
        data = schema_resp.json()
        assert data["source_type"] == "postgresql"
        assert len(data["tables"]) == 2
        table_names = [t["table_name"] for t in data["tables"]]
        assert "customers" in table_names
        assert "orders" in table_names
        assert "Tablo" in data["schema_text"]
        # İlişki meta-verisi doğru mu?
        orders_table = next(t for t in data["tables"] if t["table_name"] == "orders")
        assert len(orders_table["foreign_keys"]) == 1


# ===========================================================================
# Disconnect — üç kaynak tipi için ortak davranış
# ===========================================================================

class TestDisconnect:
    """DELETE /connect-db/disconnect/{session_id} — genel davranış"""

    @pytest.mark.parametrize("source_type,payload,connector_patch", [
        (
            "postgresql",
            {"source_type": "postgresql", "connection_url": "postgresql+psycopg2://postgres:3456@localhost:5432/db"},
            "src.api.v1.endpoints.connect_db.PostgresConnector",
        ),
        (
            "mongodb",
            {"source_type": "mongodb", "mongodb_uri": "mongodb://localhost:27017/mydb"},
            "src.api.v1.endpoints.connect_db.MongoConnector",
        ),
    ])
    def test_disconnect_closes_session(self, source_type, payload, connector_patch):
        """Bağlantı kesildikten sonra session store'dan silinir."""
        with patch(connector_patch) as mock_cls:
            mock_inst = MagicMock()
            mock_inst.test_connection.return_value = {"ok": True, "message": "OK"}
            mock_cls.return_value = mock_inst

            connect_resp = client.post("/api/v1/connect-db/connect", json=payload)
            session_id = connect_resp.json()["session_id"]

            disc_resp = client.delete(f"/api/v1/connect-db/disconnect/{session_id}")
            assert disc_resp.status_code == 200
            assert disc_resp.json()["ok"] is True
            assert disc_resp.json()["session_id"] == session_id

            # Kapatılan session artık erişilemez olmalı
            assert session_store.get_connector(session_id) is None
            mock_inst.close.assert_called_once()

    def test_disconnect_nonexistent_session(self):
        """Olmayan session 404 döner."""
        response = client.delete("/api/v1/connect-db/disconnect/sess_nonexistent")
        assert response.status_code == 404
