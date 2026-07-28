from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.api.v1.schemas.chat import ChatResponse
from src.utils.cache import query_cache
from src.utils.session_store import session_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_e2e_state():
    session_store.clear_all()
    query_cache.clear()
    yield
    query_cache.clear()
    session_store.clear_all()


@patch("src.api.v1.endpoints.chat._generate_insight_from_orchestrator")
@patch("src.api.v1.endpoints.chat.Orchestrator")
@patch("src.api.v1.endpoints.connect_db.PostgresConnector")
def test_e2e_connect_schema_chat_and_disconnect_flow(
    mock_postgres_connector,
    mock_orchestrator,
    mock_generate_insight,
):
    connector = MagicMock()
    connector.test_connection.return_value = {
        "ok": True,
        "message": "PostgreSQL connection successful.",
        "version": "15.0",
        "database": "analytics",
    }
    connector.extract_schema.return_value = {
        "tables": [
            {
                "table_name": "sales",
                "columns": [
                    {"name": "date", "type": "date"},
                    {"name": "revenue", "type": "numeric"},
                ],
            }
        ]
    }
    connector.schema_to_prompt.return_value = "Table: sales(date, revenue)"

    mock_postgres_connector.return_value = connector

    connect_payload = {
        "source_type": "postgresql",
        "connection_url": "postgresql+psycopg2://user:pass@localhost:5432/analytics",
    }

    connect_response = client.post("/api/v1/connect-db/connect", json=connect_payload)

    assert connect_response.status_code == 200

    connect_body = connect_response.json()
    session_id = connect_body["session_id"]
    source_id = connect_body["source_id"]

    assert connect_body["status"] == "connected"
    assert connect_body["source_type"] == "postgresql"
    assert session_id.startswith("sess_")
    assert source_id

    schema_response = client.get(f"/api/v1/connect-db/schema/{session_id}")

    assert schema_response.status_code == 200

    schema_body = schema_response.json()
    assert schema_body["source_type"] == "postgresql"
    assert schema_body["tables"][0]["table_name"] == "sales"
    assert "sales" in schema_body["schema_text"]

    orchestrator_result = MagicMock()
    mock_orchestrator.return_value.run.return_value = orchestrator_result

    mock_generate_insight.return_value = ChatResponse(
        status="success",
        summary="Revenue trend analysis completed.",
        sql_query="SELECT date, SUM(revenue) AS revenue FROM sales GROUP BY date",
        chart_data=[
            {"date": "2026-07-01", "revenue": 12000},
            {"date": "2026-07-02", "revenue": 13200},
        ],
        action_plan=["Monitor daily revenue trend."],
        sources_queried=[
            {
                "source_id": source_id,
                "alias": None,
                "source_type": "postgresql",
                "success": True,
                "row_count": 2,
                "error": None,
            }
        ],
    )

    chat_payload = {
        "session_id": session_id,
        "question": "Son iki günün ciro trendini analiz et.",
        "source_selection": [
            {
                "source_id": source_id,
                "tables": ["sales"],
            }
        ],
    }

    chat_response = client.post("/api/v1/chat/ask", json=chat_payload)

    assert chat_response.status_code == 200

    chat_body = chat_response.json()
    assert chat_body["status"] == "success"
    assert chat_body["summary"] == "Revenue trend analysis completed."
    assert chat_body["sql_query"].startswith("SELECT date")
    assert chat_body["chart_data"][0]["date"] == "2026-07-01"
    assert chat_body["chart_data"][0]["revenue"] == 12000
    assert chat_body["action_plan"] == ["Monitor daily revenue trend."]
    assert chat_body["sources_queried"][0]["source_id"] == source_id
    assert chat_body["sources_queried"][0]["success"] is True

    mock_orchestrator.assert_called_once()
    mock_orchestrator.return_value.run.assert_called_once()

    disconnect_response = client.delete(f"/api/v1/connect-db/disconnect/{session_id}")

    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["session_id"] == session_id
    assert session_store.get_connector(session_id) is None
