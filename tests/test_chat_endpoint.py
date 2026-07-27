import pytest
from fastapi.testclient import TestClient

from main import app
from src.api.v1.schemas.chat import ChatResponse
from src.utils.cache import make_cache_key, query_cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_chat_cache():
    query_cache.clear()
    yield
    query_cache.clear()


def test_chat_ask_returns_mock_response():
    response = client.post(
        "/api/v1/chat/ask",
        json={
            "session_id": "sess_abc123",
            "question": "Son 3 ayda en yüksek ciroyu hangi kategori üretti?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert "summary" in data
    assert "sql_query" in data
    assert isinstance(data["chart_data"], list)
    assert isinstance(data["action_plan"], list)


def test_chat_ask_rejects_empty_session_id():
    response = client.post(
        "/api/v1/chat/ask",
        json={
            "session_id": "   ",
            "question": "Son 3 ayda en yüksek ciroyu hangi kategori üretti?",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "session_id boş olamaz."


def test_chat_ask_rejects_empty_question():
    response = client.post(
        "/api/v1/chat/ask",
        json={
            "session_id": "sess_abc123",
            "question": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "question boş olamaz."


def test_chat_ask_requires_question_field():
    response = client.post(
        "/api/v1/chat/ask",
        json={
            "session_id": "sess_abc123",
        },
    )

    assert response.status_code == 422


def test_chat_ask_stores_response_in_cache():
    payload = {
        "session_id": "sess_abc123",
        "question": "Son 3 ayda en yüksek ciroyu hangi kategori üretti?",
    }

    response = client.post("/api/v1/chat/ask", json=payload)

    assert response.status_code == 200

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
    )
    cached_response = query_cache.get(cache_key)

    assert isinstance(cached_response, ChatResponse)
    assert cached_response.status == "success"


def test_chat_ask_returns_cached_response_when_available():
    payload = {
        "session_id": "sess_cached",
        "question": "Cache test sorusu",
    }

    cached_response = ChatResponse(
        status="success",
        summary="Cached response",
        sql_query=None,
        chart_data=[],
        action_plan=["Returned from cache"],
    )

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
    )
    query_cache.set(cache_key, cached_response)

    response = client.post("/api/v1/chat/ask", json=payload)

    assert response.status_code == 200
    assert response.json()["summary"] == "Cached response"
    assert response.json()["action_plan"] == ["Returned from cache"]