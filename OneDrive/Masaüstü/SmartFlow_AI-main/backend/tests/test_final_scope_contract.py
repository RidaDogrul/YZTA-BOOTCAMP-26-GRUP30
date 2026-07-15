from app.routers import ai_tasks
from app.tools import (
    TOOL_DECLARATIONS,
    check_stock_alerts,
    draft_supplier_email,
    generate_daily_briefing,
)


def _tool_names() -> set[str]:
    declarations = TOOL_DECLARATIONS[0].function_declarations
    return {declaration.name for declaration in declarations}


def test_final_scope_exposes_documented_api_contract(client):
    expected_routes = {
        ("POST", "/api/chat"),
        ("GET", "/api/orders"),
        ("GET", "/api/orders/{order_id}"),
        ("GET", "/api/products"),
        ("GET", "/api/shipments"),
        ("GET", "/api/dashboard/summary"),
        ("GET", "/api/tasks"),
        ("POST", "/api/tasks/generate"),
        ("POST", "/api/alerts/send"),
        ("POST", "/api/seed"),
        ("GET", "/health"),
    }
    actual_routes = {
        (method, route.path)
        for route in client.app.routes
        for method in getattr(route, "methods", set())
    }
    assert expected_routes <= actual_routes


def test_final_scope_declares_all_required_ai_tools():
    assert _tool_names() == {
        "get_order_status",
        "get_product_info",
        "get_cargo_status",
        "check_stock_alerts",
        "draft_supplier_email",
        "generate_daily_briefing",
        "send_manager_alert",
    }


def test_case_1_customer_order_question_returns_data_aware_reply(client):
    client.post("/api/seed")
    response = client.post("/api/chat", json={"message": "128 numaralı siparişim nerede?"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "ORDER_STATUS"
    assert body["entities"]["order_id"] == 128
    assert body["tool_calls"] == ["get_order_status"]
    assert "128 numaralı siparişiniz" in body["reply"]
    assert "Bugün 17:00" in body["reply"]

    messages = client.get("/api/messages").json()
    assert messages[0]["customer_message"] == "128 numaralı siparişim nerede?"
    assert messages[0]["intent"] == "ORDER_STATUS"


def test_case_2_products_orders_and_dashboard_summary_are_consistent(client):
    client.post("/api/seed")

    orders = client.get("/api/orders").json()
    products = client.get("/api/products").json()
    summary = client.get("/api/dashboard/summary").json()

    assert len(orders) == summary["total_orders"] == 12
    assert summary == {
        "total_orders": 12,
        "preparing_orders": 5,
        "in_cargo_orders": 4,
        "delivered_orders": 3,
        "delayed_orders": 1,
        "critical_stock_products": 2,
        "pending_tasks": 2,
        "ai_summary": "",
    }

    zeytinyagi = next(product for product in products if product["product_id"] == "P002")
    assert zeytinyagi["product_name"] == "Organik Zeytinyağı"
    assert zeytinyagi["stock_count"] == 4
    assert zeytinyagi["is_critical"] is True


def test_case_2_product_question_returns_stock_from_structured_data(client):
    client.post("/api/seed")
    response = client.post("/api/chat", json={"message": "Organik zeytinyağı var mı?"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "PRODUCT_INFO"
    assert body["entities"]["product_id"] == "P002"
    assert body["tool_calls"] == ["get_product_info"]
    assert "Organik Zeytinyağı" in body["reply"]
    assert "4 adet" in body["reply"]
    assert "Kritik seviyede" in body["reply"]


def test_case_3_delayed_cargo_question_creates_dashboard_note(client):
    client.post("/api/seed")
    response = client.post("/api/chat", json={"message": "142 numaralı siparişim neden gelmedi?"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "CARGO_STATUS"
    assert body["entities"]["order_id"] == 142
    assert body["tool_calls"] == ["get_order_status", "get_cargo_status"]
    assert "2 günlük gecikme" in body["reply"]
    assert "Ankara Aktarma Merkezi" in body["reply"]
    assert body["dashboard_note"] == "142 numaralı sipariş için gecikme uyarısı oluşturuldu."


def test_case_3_manager_alert_endpoint_sends_subject_and_body(client, monkeypatch):
    sent_payloads = []

    def fake_send(subject: str, body: str) -> bool:
        sent_payloads.append({"subject": subject, "body": body})
        return True

    monkeypatch.setattr("app.routers.alerts.send_manager_alert_email", fake_send)

    response = client.post(
        "/api/alerts/send",
        json={
            "subject": "Kargo Gecikme Uyarısı - Sipariş #142",
            "body": "142 numaralı sipariş 2 gündür gecikmiş görünüyor.",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"sent": True}
    assert sent_payloads == [
        {
            "subject": "Kargo Gecikme Uyarısı - Sipariş #142",
            "body": "142 numaralı sipariş 2 gündür gecikmiş görünüyor.",
        }
    ]


def test_case_4_stock_alerts_and_supplier_email_draft_match_mvp(db, client):
    client.post("/api/seed")

    alerts = check_stock_alerts(db)
    names = {product["product_name"] for product in alerts["products"]}
    assert alerts["critical_count"] == 2
    assert {"Organik Zeytinyağı", "Domates Salçası"} <= names

    draft = draft_supplier_email(db, "P002")
    assert draft["to"] == "zeytinyagi@example.com"
    assert draft["subject"] == "Organik Zeytinyağı Stok Yenileme Talebi"
    assert "mevcut: 4 adet" in draft["body"]
    assert "eşik: 5 adet" in draft["body"]


def test_case_4_stock_alert_chat_lists_critical_products(client):
    client.post("/api/seed")
    response = client.post("/api/chat", json={"message": "Kritik stokları listele"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "STOCK_ALERT"
    assert body["tool_calls"] == ["check_stock_alerts"]
    assert "Organik Zeytinyağı" in body["reply"]
    assert "Domates Salçası" in body["reply"]


def test_case_5_daily_briefing_endpoint_uses_cached_tool_data(client):
    client.post("/api/seed")
    ai_tasks._briefing_cache.clear()

    first = client.post("/api/tasks/generate")
    second = client.post("/api/tasks/generate")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    body = first.json()
    assert body["tool_calls"] == ["generate_daily_briefing", "check_stock_alerts"]
    assert body["data"]["summary"]["total_orders"] == 12
    assert body["data"]["delayed_orders"] == [{"order_id": 142, "customer_name": "Fatma Kaya"}]
    assert "Bugünkü Operasyon Özeti" in body["briefing"]
    assert "2 ürün kritik stok" in body["briefing"]


def test_case_5_daily_briefing_tool_returns_required_operational_context(db, client):
    client.post("/api/seed")

    data = generate_daily_briefing(db)
    task_descriptions = {task["description"] for task in data["pending_tasks"]}

    assert data["summary"]["preparing_orders"] == 5
    assert data["summary"]["in_cargo_orders"] == 4
    assert data["critical_products"] == [
        {"product_name": "Organik Zeytinyağı", "stock_count": 4},
        {"product_name": "Domates Salçası", "stock_count": 3},
    ]
    assert "#142 numaralı gecikmiş siparişin müşterisini bilgilendir." in task_descriptions
    assert "#128 ve #134 numaralı siparişleri paketle." in task_descriptions
