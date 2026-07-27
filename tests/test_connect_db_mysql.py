"""
MySQL connect_db endpoint testleri.

Bu testler MySQLConnector'ü mock'layarak gerçek bir MySQL sunucusuna
ihtiyaç duymadan endpoint'lerin doğru çalıştığını doğrular.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.utils.session_store import session_store


@pytest.fixture(autouse=True)
def clear_sessions():
    """Her testten önce ve sonra session store'u temizle."""
    session_store.clear_all()
    yield
    session_store.clear_all()


client = TestClient(app)


class TestMySQLConnectionTest:
    """MySQL bağlantı testi endpoint'i (/connect-db/test) için testler."""

    @patch("src.api.v1.endpoints.connect_db.MySQLConnector")
    def test_successful_connection(self, mock_connector_class):
        """Başarılı MySQL bağlantı testi."""
        # Mock connector instance
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "MySQL bağlantısı başarılı.",
            "version": "MySQL 8.0.34",
        }
        mock_connector_class.return_value = mock_instance

        # Request
        payload = {
            "source_type": "mysql",
            "connection_url": "mysql+pymysql://testuser:3456@localhost:3307/testdb",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["source_type"] == "mysql"
        assert "MySQL" in data["message"]
        assert data["version"] == "MySQL 8.0.34"

        # Connector mock doğru parametrelerle çağrıldı mı?
        mock_connector_class.assert_called_once_with(payload["connection_url"])
        mock_instance.test_connection.assert_called_once()

    @patch("src.api.v1.endpoints.connect_db.MySQLConnector")
    def test_connection_failed(self, mock_connector_class):
        """Başarısız MySQL bağlantı testi."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": False,
            "message": "Bağlantı hatası: Access denied for user 'testuser'@'localhost'",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "mysql",
            "connection_url": "mysql+pymysql://testuser:wrong@localhost:3307/testdb",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        # Bağlantı hatası 500 döner
        assert response.status_code == 500
        assert "Bağlantı hatası" in response.json()["detail"]

    def test_missing_connection_url(self):
        """connection_url eksikse 400 hatası döner."""
        payload = {
            "source_type": "mysql",
            # connection_url yok
        }
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 400
        assert "connection_url zorunludur" in response.json()["detail"]


class TestMySQLConnect:
    """MySQL oturum açma endpoint'i (/connect-db/connect) için testler."""

    @patch("src.api.v1.endpoints.connect_db.MySQLConnector")
    def test_successful_connect(self, mock_connector_class):
        """Başarılı MySQL oturum açma ve session_id dönüşü."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "MySQL bağlantısı başarılı.",
            "version": "MySQL 8.0.34",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "mysql",
            "connection_url": "mysql+pymysql://testuser:3456@localhost:3307/testdb",
        }
        response = client.post("/api/v1/connect-db/connect", json=payload)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["source_type"] == "mysql"
        assert "MySQL veritabanına bağlandı" in data["message"]
        assert "session_id" in data
        assert data["session_id"].startswith("sess_")

        # Session store'da kaydedildi mi?
        session_info = session_store.get_session_info(data["session_id"])
        assert session_info is not None
        assert session_info["source_type"] == "mysql"

    @patch("src.api.v1.endpoints.connect_db.MySQLConnector")
    def test_connect_with_failed_test(self, mock_connector_class):
        """Bağlantı testi başarısızsa oturum açılmaz."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": False,
            "message": "Bağlantı hatası: Unknown database 'testdb'",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "mysql",
            "connection_url": "mysql+pymysql://testuser:3456@localhost:3307/wrongdb",
        }
        response = client.post("/api/v1/connect-db/connect", json=payload)

        assert response.status_code == 500
        assert "Unknown database" in response.json()["detail"]

        # Session oluşturulmamış olmalı
        assert len(session_store.list_sessions()) == 0


class TestMySQLSchema:
    """MySQL şema endpoint'i (/connect-db/schema/{session_id}) için testler."""

    @patch("src.api.v1.endpoints.connect_db.MySQLConnector")
    def test_get_schema_success(self, mock_connector_class):
        """Başarılı şema çıkarma."""
        # Önce bir session aç
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "MySQL bağlantısı başarılı.",
        }
        mock_instance.extract_schema.return_value = {
            "tables": [
                {
                    "table_name": "users",
                    "columns": [
                        {"name": "id", "type": "INT", "primary_key": True},
                        {"name": "name", "type": "VARCHAR(100)", "primary_key": False},
                    ],
                    "foreign_keys": [],
                }
            ]
        }
        mock_instance.schema_to_prompt.return_value = (
            "Tablo: users\n  - id: INT [PK]\n  - name: VARCHAR(100)"
        )
        mock_connector_class.return_value = mock_instance

        # Connect
        payload = {
            "source_type": "mysql",
            "connection_url": "mysql+pymysql://testuser:3456@localhost:3307/testdb",
        }
        connect_response = client.post("/api/v1/connect-db/connect", json=payload)
        session_id = connect_response.json()["session_id"]

        # Get schema
        schema_response = client.get(f"/api/v1/connect-db/schema/{session_id}")

        assert schema_response.status_code == 200
        schema_data = schema_response.json()
        assert schema_data["source_type"] == "mysql"
        assert "users" in schema_data["schema_text"]
        assert len(schema_data["tables"]) == 1
        assert schema_data["tables"][0]["table_name"] == "users"

    def test_get_schema_invalid_session(self):
        """Geçersiz session_id ile 404 hatası."""
        response = client.get("/api/v1/connect-db/schema/invalid_session_id")

        assert response.status_code == 404
        assert "Oturum bulunamadı" in response.json()["detail"]


class TestMySQLDisconnect:
    """MySQL oturum kapatma endpoint'i (/connect-db/disconnect/{session_id}) için testler."""

    @patch("src.api.v1.endpoints.connect_db.MySQLConnector")
    def test_disconnect_success(self, mock_connector_class):
        """Başarılı oturum kapatma."""
        # Önce bir session aç
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = {
            "ok": True,
            "message": "MySQL bağlantısı başarılı.",
        }
        mock_connector_class.return_value = mock_instance

        payload = {
            "source_type": "mysql",
            "connection_url": "mysql+pymysql://testuser:3456@localhost:3307/testdb",
        }
        connect_response = client.post("/api/v1/connect-db/connect", json=payload)
        session_id = connect_response.json()["session_id"]

        # Disconnect
        disconnect_response = client.delete(f"/api/v1/connect-db/disconnect/{session_id}")

        assert disconnect_response.status_code == 200
        data = disconnect_response.json()
        assert data["ok"] is True
        assert data["session_id"] == session_id

        # Session kapatıldı mı?
        assert session_store.get_connector(session_id) is None
        mock_instance.close.assert_called_once()

    def test_disconnect_invalid_session(self):
        """Geçersiz session_id ile 404 hatası."""
        response = client.delete("/api/v1/connect-db/disconnect/invalid_session_id")

        assert response.status_code == 404
        assert "Oturum bulunamadı" in response.json()["detail"]


class TestMySQLSessionList:
    """Session listeme endpoint'i (/connect-db/sessions) için testler."""

    @patch("src.api.v1.endpoints.connect_db.MySQLConnector")
    @patch("src.api.v1.endpoints.connect_db.PostgresConnector")
    def test_list_multiple_sessions(self, mock_pg_class, mock_mysql_class):
        """Birden fazla oturumu listeleme."""
        # Mock MySQL
        mock_mysql = MagicMock()
        mock_mysql.test_connection.return_value = {"ok": True, "message": "OK"}
        mock_mysql_class.return_value = mock_mysql

        # Mock PostgreSQL
        mock_pg = MagicMock()
        mock_pg.test_connection.return_value = {"ok": True, "message": "OK"}
        mock_pg_class.return_value = mock_pg

        # İki oturum aç
        client.post(
            "/api/v1/connect-db/connect",
            json={
                "source_type": "mysql",
                "connection_url": "mysql+pymysql://testuser:3456@localhost:3307/testdb",
            },
        )
        client.post(
            "/api/v1/connect-db/connect",
            json={
                "source_type": "postgresql",
                "connection_url": "postgresql+psycopg2://postgres:3456@localhost:5432/mydb",
            },
        )

        # List sessions
        response = client.get("/api/v1/connect-db/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["sessions"]) == 2

        # Source type'lar doğru mu?
        source_types = {s["source_type"] for s in data["sessions"]}
        assert source_types == {"mysql", "postgresql"}
