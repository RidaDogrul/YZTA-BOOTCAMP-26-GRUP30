from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Message, Order, Product, Shipment, Task

PRODUCTS = [
    {
        "product_id": "P001",
        "product_name": "Lavanta Sabunu",
        "stock_count": 14,
        "critical_threshold": 5,
        "supplier_email": "tedarikci@example.com",
        "price": 45.0,
        "available": True,
    },
    {
        "product_id": "P002",
        "product_name": "Organik Zeytinyağı",
        "stock_count": 4,
        "critical_threshold": 5,
        "supplier_email": "zeytinyagi@example.com",
        "price": 120.0,
        "available": True,
    },
    {
        "product_id": "P003",
        "product_name": "Çiçek Balı",
        "stock_count": 22,
        "critical_threshold": 8,
        "supplier_email": "bal@example.com",
        "price": 85.0,
        "available": True,
    },
    {
        "product_id": "P004",
        "product_name": "Domates Salçası",
        "stock_count": 3,
        "critical_threshold": 10,
        "supplier_email": "salca@example.com",
        "price": 35.0,
        "available": True,
    },
    {
        "product_id": "P005",
        "product_name": "Kuru İncir",
        "stock_count": 18,
        "critical_threshold": 6,
        "supplier_email": "incir@example.com",
        "price": 60.0,
        "available": True,
    },
    {
        "product_id": "P006",
        "product_name": "Gül Reçeli",
        "stock_count": 9,
        "critical_threshold": 5,
        "supplier_email": "recel@example.com",
        "price": 55.0,
        "available": True,
    },
]

ORDERS = [
    # Demo siparişleri — doküman §15 demo akışı
    {
        "order_id": 128,
        "customer_name": "Ayşe Demir",
        "customer_phone": "05321111111",
        "product_id": "P001",
        "quantity": 2,
        "status": "Kargoda",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Bugün 17:00",
    },
    {
        "order_id": 134,
        "customer_name": "Mehmet Yılmaz",
        "customer_phone": "05322222222",
        "product_id": "P003",
        "quantity": 1,
        "status": "Hazırlanıyor",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Yarın",
    },
    {
        "order_id": 142,
        "customer_name": "Fatma Kaya",
        "customer_phone": "05323333333",
        "product_id": "P002",
        "quantity": 1,
        "status": "Kargoda",
        "cargo_status": "Gecikmiş",
        "estimated_delivery": "Yarın",
    },
    # Ek siparişler (toplam 12)
    {
        "order_id": 120,
        "customer_name": "Ali Çelik",
        "customer_phone": "05324444444",
        "product_id": "P005",
        "quantity": 3,
        "status": "Teslim Edildi",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Teslim Edildi",
    },
    {
        "order_id": 121,
        "customer_name": "Zeynep Arslan",
        "customer_phone": "05325555555",
        "product_id": "P006",
        "quantity": 2,
        "status": "Teslim Edildi",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Teslim Edildi",
    },
    {
        "order_id": 122,
        "customer_name": "Hasan Öztürk",
        "customer_phone": "05326666666",
        "product_id": "P004",
        "quantity": 4,
        "status": "Hazırlanıyor",
        "cargo_status": "Zamanında",
        "estimated_delivery": "2 gün sonra",
    },
    {
        "order_id": 123,
        "customer_name": "Elif Şahin",
        "customer_phone": "05327777777",
        "product_id": "P001",
        "quantity": 1,
        "status": "Hazırlanıyor",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Yarın",
    },
    {
        "order_id": 124,
        "customer_name": "Mustafa Koç",
        "customer_phone": "05328888888",
        "product_id": "P003",
        "quantity": 2,
        "status": "Hazırlanıyor",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Yarın",
    },
    {
        "order_id": 125,
        "customer_name": "Selin Aydın",
        "customer_phone": "05329999999",
        "product_id": "P005",
        "quantity": 1,
        "status": "Kargoda",
        "cargo_status": "Dağıtımda",
        "estimated_delivery": "Bugün",
    },
    {
        "order_id": 126,
        "customer_name": "Burak Doğan",
        "customer_phone": "05330000000",
        "product_id": "P006",
        "quantity": 3,
        "status": "Kargoda",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Yarın",
    },
    {
        "order_id": 127,
        "customer_name": "Nalan Yıldız",
        "customer_phone": "05331111111",
        "product_id": "P002",
        "quantity": 2,
        "status": "Hazırlanıyor",
        "cargo_status": "Zamanında",
        "estimated_delivery": "2 gün sonra",
    },
    {
        "order_id": 129,
        "customer_name": "Oğuz Bal",
        "customer_phone": "05332222222",
        "product_id": "P004",
        "quantity": 1,
        "status": "Teslim Edildi",
        "cargo_status": "Zamanında",
        "estimated_delivery": "Teslim Edildi",
    },
]

SHIPMENTS = [
    {
        "shipment_id": 1,
        "order_id": 128,
        "carrier": "Yurtiçi Kargo",
        "tracking_number": "YK20240128",
        "actual_status": "Dağıtımda",
        "last_location": "İstanbul Dağıtım Merkezi",
        "delay_days": 0,
        "estimated_delivery": "Bugün 17:00",
    },
    {
        "shipment_id": 2,
        "order_id": 134,
        "carrier": "Aras Kargo",
        "tracking_number": "AR20240134",
        "actual_status": "Yolda",
        "last_location": "Ankara Çıkış Merkezi",
        "delay_days": 0,
        "estimated_delivery": "Yarın",
    },
    {
        "shipment_id": 3,
        "order_id": 142,
        "carrier": "MNG Kargo",
        "tracking_number": "MN20240142",
        "actual_status": "Gecikmiş",
        "last_location": "Ankara Aktarma Merkezi",
        "delay_days": 2,
        "estimated_delivery": "Yarın",
    },
    {
        "shipment_id": 4,
        "order_id": 120,
        "carrier": "PTT Kargo",
        "tracking_number": "PT20240120",
        "actual_status": "Teslim Edildi",
        "last_location": "Teslim Noktası",
        "delay_days": 0,
        "estimated_delivery": "Teslim Edildi",
    },
    {
        "shipment_id": 5,
        "order_id": 121,
        "carrier": "Yurtiçi Kargo",
        "tracking_number": "YK20240121",
        "actual_status": "Teslim Edildi",
        "last_location": "Teslim Noktası",
        "delay_days": 0,
        "estimated_delivery": "Teslim Edildi",
    },
    {
        "shipment_id": 6,
        "order_id": 122,
        "carrier": "Aras Kargo",
        "tracking_number": "AR20240122",
        "actual_status": "Yolda",
        "last_location": "İzmir Merkez",
        "delay_days": 0,
        "estimated_delivery": "2 gün sonra",
    },
    {
        "shipment_id": 7,
        "order_id": 123,
        "carrier": "MNG Kargo",
        "tracking_number": "MN20240123",
        "actual_status": "Yolda",
        "last_location": "İstanbul Merkez",
        "delay_days": 0,
        "estimated_delivery": "Yarın",
    },
    {
        "shipment_id": 8,
        "order_id": 124,
        "carrier": "Yurtiçi Kargo",
        "tracking_number": "YK20240124",
        "actual_status": "Yolda",
        "last_location": "Bursa Merkez",
        "delay_days": 0,
        "estimated_delivery": "Yarın",
    },
    {
        "shipment_id": 9,
        "order_id": 125,
        "carrier": "PTT Kargo",
        "tracking_number": "PT20240125",
        "actual_status": "Dağıtımda",
        "last_location": "Adana Dağıtım",
        "delay_days": 0,
        "estimated_delivery": "Bugün",
    },
    {
        "shipment_id": 10,
        "order_id": 126,
        "carrier": "Aras Kargo",
        "tracking_number": "AR20240126",
        "actual_status": "Yolda",
        "last_location": "Konya Merkez",
        "delay_days": 0,
        "estimated_delivery": "Yarın",
    },
    {
        "shipment_id": 11,
        "order_id": 127,
        "carrier": "MNG Kargo",
        "tracking_number": "MN20240127",
        "actual_status": "Yolda",
        "last_location": "Ankara Merkez",
        "delay_days": 0,
        "estimated_delivery": "2 gün sonra",
    },
    {
        "shipment_id": 12,
        "order_id": 129,
        "carrier": "Yurtiçi Kargo",
        "tracking_number": "YK20240129",
        "actual_status": "Teslim Edildi",
        "last_location": "Teslim Noktası",
        "delay_days": 0,
        "estimated_delivery": "Teslim Edildi",
    },
]

TASKS = [
    {
        "task_type": "Müşteri Bilgilendirme",
        "description": "#142 numaralı gecikmiş siparişin müşterisini bilgilendir.",
        "priority": "Yüksek",
        "status": "Bekliyor",
        "related_order_id": 142,
        "related_product_id": None,
    },
    {
        "task_type": "Paketleme",
        "description": "#128 ve #134 numaralı siparişleri paketle.",
        "priority": "Orta",
        "status": "Bekliyor",
        "related_order_id": 128,
        "related_product_id": None,
    },
    {
        "task_type": "Stok",
        "description": "Organik Zeytinyağı için tedarikçi mail taslağını kontrol et ve onayla.",
        "priority": "Yüksek",
        "status": "Onay bekliyor",
        "related_order_id": None,
        "related_product_id": "P002",
    },
]


def run_seed(db: Session) -> dict[str, int]:
    for model in (Message, Task, Shipment, Order, Product):
        db.query(model).delete()
    db.commit()

    for data in PRODUCTS:
        db.add(Product(**data))
    db.commit()

    now = datetime.now(timezone.utc)
    for data in ORDERS:
        db.add(Order(**data, created_at=now))
    db.commit()

    for data in SHIPMENTS:
        db.add(Shipment(**data))
    db.commit()

    for data in TASKS:
        db.add(Task(**data))
    db.commit()

    return {
        "products": len(PRODUCTS),
        "orders": len(ORDERS),
        "shipments": len(SHIPMENTS),
        "tasks": len(TASKS),
        "messages": 0,
    }
