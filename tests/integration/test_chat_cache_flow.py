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


def test_chat_endpoint_generates_response_and_stores_it_in_cache():
    payload = {
        "session_id": "sess_integration_001",
        "question": "Son 3 ayda en yüksek ciroyu hangi kategori üretti?",
    }

    response = client.post("/api/v1/chat/ask", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert "summary" in body
    assert "sql_query" in body
    assert isinstance(body["chart_data"], list)
    assert isinstance(body["action_plan"], list)

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
    )

    cached_response = query_cache.get(cache_key)

    assert isinstance(cached_response, ChatResponse)
    assert cached_response.status == "success"


def test_chat_endpoint_returns_cached_response_for_repeated_request():
    payload = {
        "session_id": "sess_integration_cache",
        "question": "Cache entegrasyon testi sorusu",
    }

    first_response = client.post("/api/v1/chat/ask", json=payload)
    second_response = client.post("/api/v1/chat/ask", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
    )

    assert query_cache.get(cache_key) is not None


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