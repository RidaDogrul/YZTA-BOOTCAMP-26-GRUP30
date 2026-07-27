"""
Snowflake connect_db endpoint testleri.

Mock tabanlı unit testler — gerçek Snowflake hesabı gerektirmez.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.connectors.snowflake_conn import SnowflakeConfig
from src.utils.session_store import session_store

client = TestClient(app)

# ---------------------------------------------------------------------------
# Yardımcı sabitler
# ---------------------------------------------------------------------------
_VALID_PAYLOAD = {
    "source_type": "snowflake",
    "snowflake_account": "xy12345.eu-central-1",
    "snowflake_user": "myuser",
    "snowflake_password": "mypassword",
    "snowflake_database": "MY_DB",
    "snowflake_schema": "PUBLIC",
    "snowflake_warehouse": "COMPUTE_WH",
    "snowflake_role": "SYSADMIN",
}

_MOCK_TEST_OK = {
    "ok": True,
    "message": "Snowflake bağlantısı başarılı.",
    "version": "8.18.0",
    "warehouse": "COMPUTE_WH",
    "database": "MY_DB",
    "schema": "PUBLIC",
}


@pytest.fixture(autouse=True)
def clear_sessions():
    """Her testten önce/sonra session store'u temizle."""
    session_store.clear_all()
    yield
    session_store.clear_all()


# ===========================================================================
# SnowflakeConfig unit testleri
# ===========================================================================

class TestSnowflakeConfig:
    """SnowflakeConfig model ve URL üretimi testleri."""

    def test_to_url_with_all_params(self):
        """Tüm parametrelerle doğru URL üretilir."""
        config = SnowflakeConfig(
            account="xy12345.eu-central-1",
            user="myuser",
            password="mypassword",
            database="MY_DB",
            schema_name="PUBLIC",
            warehouse="COMPUTE_WH",
            role="SYSADMIN",
        )
        url = config.to_url()
        assert url.startswith("snowflake://myuser:mypassword@xy12345.eu-central-1/MY_DB/PUBLIC")
        assert "warehouse=COMPUTE_WH" in url
        assert "role=SYSADMIN" in url

    def test_to_url_without_optional_params(self):
        """Warehouse ve role olmadan da geçerli URL üretilir."""
        config = SnowflakeConfig(
            account="xy12345.eu-central-1",
            user="myuser",
            password="mypassword",
            database="MY_DB",
        )
        url = config.to_url()
        assert "snowflake://myuser:mypassword@xy12345.eu-central-1/MY_DB/PUBLIC" in url
        assert "warehouse" not in url
        assert "role" not in url

    def test_from_url_full(self):
        """Tam URL'den config doğru ayrıştırılır."""
        url = "snowflake://myuser:mypassword@xy12345.eu-central-1/MY_DB/PUBLIC?warehouse=COMPUTE_WH&role=SYSADMIN"
        config = SnowflakeConfig.from_url(url)
        assert config.account == "xy12345.eu-central-1"
        assert config.user == "myuser"
        assert config.password.get_secret_value() == "mypassword"
        assert config.database == "MY_DB"
        assert config.schema_name == "PUBLIC"
        assert config.warehouse == "COMPUTE_WH"
        assert config.role == "SYSADMIN"

    def test_from_url_minimal(self):
        """Minimal URL'den config doğru ayrıştırılır, opsiyoneller None."""
        url = "snowflake://myuser:mypassword@xy12345.eu-central-1/MY_DB"
        config = SnowflakeConfig.from_url(url)
        assert config.account == "xy12345.eu-central-1"
        assert config.database == "MY_DB"
        assert config.schema_name == "PUBLIC"  # varsayılan
        assert config.warehouse is None
        assert config.role is None

    def test_from_url_invalid(self):
        """Geçersiz URL ValueError fırlatır."""
        with pytest.raises(ValueError, match="Geçersiz Snowflake"):
            SnowflakeConfig.from_url("postgresql://user:pass@host/db")

    def test_empty_account_raises(self):
        """Boş account alanı ValidationError fırlatır."""
        with pytest.raises(Exception):
            SnowflakeConfig(
                account="",
                user="myuser",
                password="mypassword",
                database="MY_DB",
            )

    def test_password_is_secret(self):
        """Parola SecretStr olarak saklanır, str() ile görünmez."""
        config = SnowflakeConfig(
            account="xy12345.eu-central-1",
            user="myuser",
            password="supersecret",
            database="MY_DB",
        )
        assert "supersecret" not in str(config)
        assert config.password.get_secret_value() == "supersecret"


# ===========================================================================
# POST /connect-db/test — Snowflake
# ===========================================================================

class TestSnowflakeConnectionTest:
    """Bağlantı testi endpoint testleri."""

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_successful(self, mock_cls):
        """Başarılı bağlantı testi 200 döner."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_cls.return_value = mock_inst

        response = client.post("/api/v1/connect-db/test", json=_VALID_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["source_type"] == "snowflake"
        assert data["version"] == "8.18.0"
        assert data["warehouse"] == "COMPUTE_WH"
        assert data["database"] == "MY_DB"
        assert data["snowflake_schema"] == "PUBLIC"

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_auth_failure(self, mock_cls):
        """Yanlış kimlik bilgileriyle 500 döner."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = {
            "ok": False,
            "message": "Bağlantı hatası: 250001: Failed to connect to DB: "
                       "Incorrect username or password was specified.",
        }
        mock_cls.return_value = mock_inst

        payload = {**_VALID_PAYLOAD, "snowflake_password": "wrongpass"}
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 500
        assert "Incorrect username or password" in response.json()["detail"]

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_invalid_account(self, mock_cls):
        """Yanlış account ile 500 döner."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = {
            "ok": False,
            "message": "Bağlantı hatası: 250001: Could not connect to Snowflake backend.",
        }
        mock_cls.return_value = mock_inst

        payload = {**_VALID_PAYLOAD, "snowflake_account": "invalid-account"}
        response = client.post("/api/v1/connect-db/test", json=payload)

        assert response.status_code == 500

    def test_missing_account(self):
        """snowflake_account eksikse 400 döner."""
        payload = {**_VALID_PAYLOAD}
        del payload["snowflake_account"]
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "snowflake_account" in response.json()["detail"]

    def test_missing_user(self):
        """snowflake_user eksikse 400 döner."""
        payload = {**_VALID_PAYLOAD}
        del payload["snowflake_user"]
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "snowflake_user" in response.json()["detail"]

    def test_missing_password(self):
        """snowflake_password eksikse 400 döner."""
        payload = {**_VALID_PAYLOAD}
        del payload["snowflake_password"]
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "snowflake_password" in response.json()["detail"]

    def test_missing_database(self):
        """snowflake_database eksikse 400 döner."""
        payload = {**_VALID_PAYLOAD}
        del payload["snowflake_database"]
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 400
        assert "snowflake_database" in response.json()["detail"]

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_without_warehouse_and_role(self, mock_cls):
        """Warehouse ve role olmadan da başarılı test yapılır."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = {
            "ok": True,
            "message": "Snowflake bağlantısı başarılı.",
            "version": "8.18.0",
            "warehouse": None,
            "database": "MY_DB",
            "schema": "PUBLIC",
        }
        mock_cls.return_value = mock_inst

        payload = {
            "source_type": "snowflake",
            "snowflake_account": "xy12345.eu-central-1",
            "snowflake_user": "myuser",
            "snowflake_password": "mypassword",
            "snowflake_database": "MY_DB",
        }
        response = client.post("/api/v1/connect-db/test", json=payload)
        assert response.status_code == 200
        assert response.json()["ok"] is True


# ===========================================================================
# POST /connect-db/connect — Snowflake
# ===========================================================================

class TestSnowflakeConnect:
    """Oturum açma endpoint testleri."""

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_successful_connect(self, mock_cls):
        """Başarılı bağlantı — session_id ve mesaj döner."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_cls.return_value = mock_inst

        response = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["source_type"] == "snowflake"
        assert "MY_DB" in data["message"]
        assert "COMPUTE_WH" in data["message"]
        assert data["session_id"].startswith("sess_")

        # Session store'da kaydedildi mi?
        info = session_store.get_session_info(data["session_id"])
        assert info is not None
        assert info["source_type"] == "snowflake"

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_connect_stores_connector(self, mock_cls):
        """Connector session store'a doğru kaydedilir."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_cls.return_value = mock_inst

        response = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)
        session_id = response.json()["session_id"]

        stored = session_store.get_connector(session_id)
        assert stored is mock_inst

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_connect_fails_on_bad_credentials(self, mock_cls):
        """Bağlantı başarısızsa session açılmaz."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = {
            "ok": False,
            "message": "Bağlantı hatası: Incorrect username or password.",
        }
        mock_cls.return_value = mock_inst

        response = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)

        assert response.status_code == 500
        assert len(session_store.list_sessions()) == 0

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_multiple_connects_unique_sessions(self, mock_cls):
        """Her bağlantı isteği farklı session_id üretir."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_cls.return_value = mock_inst

        r1 = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)
        r2 = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)

        assert r1.json()["session_id"] != r2.json()["session_id"]
        assert len(session_store.list_sessions()) == 2


# ===========================================================================
# GET /connect-db/schema/{session_id} — Snowflake
# ===========================================================================

class TestSnowflakeSchema:
    """Şema endpoint testleri."""

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_get_schema_tables(self, mock_cls):
        """Snowflake şeması tablo listesi döner."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_inst.extract_schema.return_value = {
            "tables": [
                {
                    "table_name": "ORDERS",
                    "columns": [
                        {"name": "ORDER_ID",   "type": "NUMBER",  "primary_key": True,  "nullable": False},
                        {"name": "CUSTOMER_ID","type": "NUMBER",  "primary_key": False, "nullable": False},
                        {"name": "ORDER_DATE", "type": "DATE",    "primary_key": False, "nullable": True},
                        {"name": "TOTAL_AMT",  "type": "FLOAT",   "primary_key": False, "nullable": True},
                    ],
                    "foreign_keys": [
                        {"columns": ["CUSTOMER_ID"], "references_table": "CUSTOMERS", "references_columns": ["ID"]}
                    ],
                },
                {
                    "table_name": "CUSTOMERS",
                    "columns": [
                        {"name": "ID",    "type": "NUMBER",       "primary_key": True,  "nullable": False},
                        {"name": "NAME",  "type": "VARCHAR(200)", "primary_key": False, "nullable": False},
                        {"name": "EMAIL", "type": "VARCHAR(200)", "primary_key": False, "nullable": True},
                    ],
                    "foreign_keys": [],
                },
            ]
        }
        mock_inst.schema_to_prompt.return_value = (
            "Tablo: ORDERS\n  - ORDER_ID: NUMBER [PK, NOT NULL]\n\n"
            "Tablo: CUSTOMERS\n  - ID: NUMBER [PK, NOT NULL]"
        )
        mock_cls.return_value = mock_inst

        # Connect
        connect_resp = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)
        session_id = connect_resp.json()["session_id"]

        # Schema
        schema_resp = client.get(f"/api/v1/connect-db/schema/{session_id}")
        assert schema_resp.status_code == 200
        data = schema_resp.json()
        assert data["source_type"] == "snowflake"
        assert len(data["tables"]) == 2
        table_names = [t["table_name"] for t in data["tables"]]
        assert "ORDERS" in table_names
        assert "CUSTOMERS" in table_names
        assert "Tablo" in data["schema_text"]

        # FK meta-verisi doğru geldi mi?
        orders = next(t for t in data["tables"] if t["table_name"] == "ORDERS")
        assert len(orders["foreign_keys"]) == 1
        assert orders["foreign_keys"][0]["references_table"] == "CUSTOMERS"

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_schema_empty_database(self, mock_cls):
        """Boş veritabanı için boş tablo listesi döner."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_inst.extract_schema.return_value = {"tables": []}
        mock_inst.schema_to_prompt.return_value = ""
        mock_cls.return_value = mock_inst

        connect_resp = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)
        session_id = connect_resp.json()["session_id"]

        schema_resp = client.get(f"/api/v1/connect-db/schema/{session_id}")
        assert schema_resp.status_code == 200
        assert schema_resp.json()["tables"] == []

    def test_schema_invalid_session(self):
        """Geçersiz session_id ile 404 döner."""
        response = client.get("/api/v1/connect-db/schema/sess_nonexistent")
        assert response.status_code == 404
        assert "Oturum bulunamadı" in response.json()["detail"]


# ===========================================================================
# DELETE /connect-db/disconnect/{session_id} — Snowflake
# ===========================================================================

class TestSnowflakeDisconnect:
    """Oturum kapatma endpoint testleri."""

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_disconnect_success(self, mock_cls):
        """Oturum başarıyla kapatılır, connector.close() çağrılır."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_cls.return_value = mock_inst

        connect_resp = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)
        session_id = connect_resp.json()["session_id"]

        disc_resp = client.delete(f"/api/v1/connect-db/disconnect/{session_id}")
        assert disc_resp.status_code == 200
        data = disc_resp.json()
        assert data["ok"] is True
        assert data["session_id"] == session_id

        # Session artık erişilemez
        assert session_store.get_connector(session_id) is None
        mock_inst.close.assert_called_once()

    def test_disconnect_invalid_session(self):
        """Olmayan session 404 döner."""
        response = client.delete("/api/v1/connect-db/disconnect/sess_nonexistent")
        assert response.status_code == 404

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_double_disconnect(self, mock_cls):
        """Aynı session iki kez disconnect edilemez."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_cls.return_value = mock_inst

        connect_resp = client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)
        session_id = connect_resp.json()["session_id"]

        client.delete(f"/api/v1/connect-db/disconnect/{session_id}")
        second = client.delete(f"/api/v1/connect-db/disconnect/{session_id}")
        assert second.status_code == 404


# ===========================================================================
# GET /connect-db/sessions — Snowflake session listeleme
# ===========================================================================

class TestSnowflakeSessions:
    """Session listeleme endpoint testleri."""

    @patch("src.api.v1.endpoints.connect_db.SnowflakeConnector")
    def test_snowflake_session_in_list(self, mock_cls):
        """Snowflake oturumu session listesinde görünür."""
        mock_inst = MagicMock()
        mock_inst.test_connection.return_value = _MOCK_TEST_OK
        mock_cls.return_value = mock_inst

        client.post("/api/v1/connect-db/connect", json=_VALID_PAYLOAD)

        response = client.get("/api/v1/connect-db/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["sessions"][0]["source_type"] == "snowflake"
