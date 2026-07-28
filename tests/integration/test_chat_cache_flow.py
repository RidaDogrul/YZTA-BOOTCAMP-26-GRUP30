import pytest
from fastapi.testclient import TestClient

from main import app
from src.api.v1.schemas.chat import ChatResponse
from src.utils.cache import make_cache_key, query_cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_query_cache():
    query_cache.clear()
    yield
    query_cache.clear()


def test_chat_endpoint_returns_cached_standard_response():
    payload = {
        "session_id": "sess_integration_cache",
        "question": "Cache entegrasyon testi sorusu",
    }

    cached_response = ChatResponse(
        status="success",
        summary="Cached integration response",
        sql_query="SELECT 1",
        chart_data=[
            {"date": "2026-07-01", "predicted_sales": 12000},
            {"date": "2026-07-02", "predicted_sales": 13200},
        ],
        action_plan=["Returned from integration cache"],
        sources_queried=[
            {
                "source_id": "src_001",
                "alias": "Satış DB",
                "source_type": "postgresql",
                "success": True,
                "row_count": 2,
                "error": None,
            }
        ],
    )

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
        "[]",
    )
    query_cache.set(cache_key, cached_response)

    response = client.post("/api/v1/chat/ask", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "success"
    assert body["summary"] == "Cached integration response"
    assert body["sql_query"] == "SELECT 1"
    assert body["chart_data"][0]["date"] == "2026-07-01"
    assert body["action_plan"] == ["Returned from integration cache"]
    assert body["sources_queried"][0]["source_id"] == "src_001"


def test_chat_endpoint_rejects_unknown_session_without_cache_write():
    payload = {
        "session_id": "sess_unknown",
        "question": "Son 3 ayda en yüksek ciroyu hangi kategori üretti?",
    }

    response = client.post("/api/v1/chat/ask", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Oturum bulunamadı veya süresi doldu."

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
        "[]",
    )

    assert query_cache.get(cache_key) is None


def test_chat_endpoint_rejects_invalid_request_without_cache_write():
    payload = {
        "session_id": "   ",
        "question": "Geçersiz session testi",
    }

    response = client.post("/api/v1/chat/ask", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "session_id boş olamaz."

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
        "[]",
    )

    assert query_cache.get(cache_key) is None


def test_chat_endpoint_requires_question_field():
    response = client.post(
        "/api/v1/chat/ask",
        json={
            "session_id": "sess_missing_question",
        },
    )

    assert response.status_code == 422
