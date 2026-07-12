from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


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