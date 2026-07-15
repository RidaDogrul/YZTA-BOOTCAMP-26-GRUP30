def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_seed(client):
    r = client.post("/api/seed")
    assert r.status_code == 200
    body = r.json()
    assert body["seeded"] is True
    assert body["counts"]["orders"] == 12
    assert body["counts"]["products"] == 6
    assert body["counts"]["shipments"] == 12
    assert body["counts"]["tasks"] == 3


def test_list_orders(client):
    client.post("/api/seed")
    r = client.get("/api/orders")
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 12
    ids = [o["order_id"] for o in orders]
    assert 128 in ids
    assert 134 in ids
    assert 142 in ids


def test_get_order_detail(client):
    client.post("/api/seed")
    r = client.get("/api/orders/142")
    assert r.status_code == 200
    order = r.json()
    assert order["order_id"] == 142
    assert order["cargo_status"] == "Gecikmiş"


def test_get_order_not_found(client):
    r = client.get("/api/orders/9999")
    assert r.status_code == 404


def test_list_products(client):
    client.post("/api/seed")
    r = client.get("/api/products")
    assert r.status_code == 200
    products = r.json()
    assert len(products) == 6
    zeytinyagi = next(p for p in products if p["product_id"] == "P002")
    assert zeytinyagi["stock_count"] == 4
    assert zeytinyagi["is_critical"] is True
    lavanta = next(p for p in products if p["product_id"] == "P001")
    assert lavanta["is_critical"] is False


def test_list_shipments(client):
    client.post("/api/seed")
    r = client.get("/api/shipments")
    assert r.status_code == 200
    shipments = r.json()
    assert len(shipments) == 12
    delayed = next(s for s in shipments if s["order_id"] == 142)
    assert delayed["delay_days"] == 2
    assert delayed["last_location"] == "Ankara Aktarma Merkezi"


def test_list_tasks(client):
    client.post("/api/seed")
    r = client.get("/api/tasks")
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) == 3
    high_priority = [t for t in tasks if t["priority"] == "Yüksek"]
    assert len(high_priority) == 2


def test_dashboard_summary(client):
    client.post("/api/seed")
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    s = r.json()
    assert s["total_orders"] == 12
    assert s["preparing_orders"] == 5
    assert s["in_cargo_orders"] == 4
    assert s["delivered_orders"] == 3
    assert s["delayed_orders"] == 1
    assert s["critical_stock_products"] == 2
    assert s["pending_tasks"] == 2


def test_generate_daily_briefing_endpoint(client):
    client.post("/api/seed")
    r = client.post("/api/tasks/generate")
    assert r.status_code == 200
    body = r.json()
    assert "Bugünkü Operasyon Özeti" in body["briefing"]
    assert "generate_daily_briefing" in body["tool_calls"]
    assert body["data"]["summary"]["total_orders"] == 12


def test_chat_fallback_uses_tools_and_persists_message(client):
    client.post("/api/seed")
    r = client.post("/api/chat", json={"message": "142 numaralı siparişim neden gelmedi?"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "CARGO_STATUS"
    assert body["entities"]["order_id"] == 142
    assert body["tool_calls"] == ["get_order_status", "get_cargo_status"]
    assert "2 günlük gecikme" in body["reply"]

    messages = client.get("/api/messages").json()
    assert len(messages) == 1
    assert messages[0]["intent"] == "CARGO_STATUS"


def test_list_messages_empty(client):
    client.post("/api/seed")
    r = client.get("/api/messages")
    assert r.status_code == 200
    assert r.json() == []
