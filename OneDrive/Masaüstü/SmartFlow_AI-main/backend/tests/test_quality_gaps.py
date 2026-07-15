from app.models import Product
from app.tools import check_stock_alerts


def test_task_status_update_succeeds_for_supported_status(client):
    client.post("/api/seed")

    response = client.patch("/api/tasks/1", json={"status": "Tamamlandı"})

    assert response.status_code == 200
    assert response.json()["status"] == "Tamamlandı"
    tasks = client.get("/api/tasks").json()
    assert next(task for task in tasks if task["task_id"] == 1)["status"] == "Tamamlandı"


def test_task_status_update_returns_404_for_missing_task(client):
    client.post("/api/seed")

    response = client.patch("/api/tasks/9999", json={"status": "Tamamlandı"})

    assert response.status_code == 404


def test_task_status_update_rejects_invalid_status_without_mutation(client):
    client.post("/api/seed")
    original = client.get("/api/tasks").json()[0]

    response = client.patch(
        f"/api/tasks/{original['task_id']}",
        json={"status": "Silindi"},
    )

    assert response.status_code == 422
    updated = client.get("/api/tasks").json()[0]
    assert updated["status"] == original["status"]


def test_chat_missing_message_payload_is_rejected(client):
    client.post("/api/seed")

    response = client.post("/api/chat", json={})

    assert response.status_code == 422
    assert client.get("/api/messages").json() == []


def test_chat_blank_message_payload_is_rejected(client):
    client.post("/api/seed")

    response = client.post("/api/chat", json={"message": "   "})

    assert response.status_code == 422
    assert client.get("/api/messages").json() == []


def test_alert_endpoint_reports_provider_failure(client, monkeypatch):
    monkeypatch.setattr("app.routers.alerts.send_manager_alert_email", lambda *_: False)

    response = client.post(
        "/api/alerts/send",
        json={"subject": "Kargo Gecikme Uyarısı", "body": "Sipariş gecikti."},
    )

    assert response.status_code == 200
    assert response.json() == {"sent": False}


def test_alert_endpoint_rejects_missing_subject(client):
    response = client.post("/api/alerts/send", json={"body": "Sipariş gecikti."})

    assert response.status_code == 422


def test_messages_limit_returns_newest_single_message(client):
    client.post("/api/seed")
    client.post("/api/chat", json={"message": "128 numaralı siparişim nerede?"})
    client.post("/api/chat", json={"message": "142 numaralı siparişim neden gelmedi?"})

    response = client.get("/api/messages?limit=1")

    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 1
    assert messages[0]["customer_message"] == "142 numaralı siparişim neden gelmedi?"


def test_stock_equal_to_threshold_is_critical(db):
    db.add(
        Product(
            product_id="P999",
            product_name="Eşik Ürünü",
            stock_count=5,
            critical_threshold=5,
            supplier_email="esik@example.com",
            price=10.0,
            available=True,
        )
    )
    db.commit()

    alerts = check_stock_alerts(db)

    product_ids = {product["product_id"] for product in alerts["products"]}
    assert "P999" in product_ids


def test_cors_preflight_allows_local_origin_and_rejects_unknown(client):
    allowed = client.options(
        "/api/orders",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    blocked = client.options(
        "/api/orders",
        headers={
            "Origin": "https://unknown.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert blocked.headers.get("access-control-allow-origin") != "https://unknown.example"
