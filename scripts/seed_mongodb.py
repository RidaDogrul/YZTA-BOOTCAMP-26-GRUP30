"""
MongoDB mydb'ye zengin e-ticaret test dataset'i yükler.

Koleksiyonlar:
  customers  — müşteri profilleri (PII içerir: name, email, phone)
  products   — ürün kataloğu
  orders     — sipariş kayıtları
  inventory  — stok hareketleri
  campaigns  — pazarlama kampanyaları

Çalıştır:
    python scripts/seed_mongodb.py
    python scripts/seed_mongodb.py --uri mongodb://user:pass@host:27017/mydb
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from random import Random

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv(PROJECT_ROOT / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/mydb")

# ---------------------------------------------------------------------------
# Sabit veriler
# ---------------------------------------------------------------------------

CUSTOMERS = [
    {"customer_id": "C001", "name": "Elif Keskin",        "email": "elif.keskin@example.com",  "phone": "05551234567", "city": "İstanbul",  "segment": "premium",  "registered_at": datetime(2025, 11, 10), "total_orders": 8,  "lifetime_value": 3240.0},
    {"customer_id": "C002", "name": "Recep Atabey Demir", "email": "recep@example.com",         "phone": "05559876543", "city": "Ankara",    "segment": "standard", "registered_at": datetime(2025, 12,  5), "total_orders": 3,  "lifetime_value":  864.0},
    {"customer_id": "C003", "name": "Nimet Asude Yalçın", "email": "nimet@example.com",         "phone": "05551112233", "city": "Sakarya",   "segment": "premium",  "registered_at": datetime(2026,  1, 15), "total_orders": 5,  "lifetime_value": 2310.0},
    {"customer_id": "C004", "name": "Rida Doğrul",        "email": "rida@example.com",          "phone": "05550001122", "city": "İzmir",     "segment": "standard", "registered_at": datetime(2026,  2, 20), "total_orders": 2,  "lifetime_value":  576.0},
    {"customer_id": "C005", "name": "Murat Şahin",        "email": "murat.sahin@example.com",   "phone": "05553334455", "city": "İstanbul",  "segment": "vip",      "registered_at": datetime(2025,  9,  3), "total_orders": 14, "lifetime_value": 6720.0},
    {"customer_id": "C006", "name": "Selin Aydın",        "email": "selin.aydin@example.com",   "phone": "05556667788", "city": "Bursa",     "segment": "standard", "registered_at": datetime(2026,  3, 11), "total_orders": 1,  "lifetime_value":  288.0},
    {"customer_id": "C007", "name": "Kerem Öztürk",       "email": "kerem.ozturk@example.com",  "phone": "05557778899", "city": "İstanbul",  "segment": "premium",  "registered_at": datetime(2025, 10, 22), "total_orders": 7,  "lifetime_value": 2940.0},
    {"customer_id": "C008", "name": "Ayşe Yıldız",        "email": "ayse.yildiz@example.com",   "phone": "05558889900", "city": "Ankara",    "segment": "vip",      "registered_at": datetime(2025,  8, 14), "total_orders": 18, "lifetime_value": 8460.0},
    {"customer_id": "C009", "name": "Burak Çelik",        "email": "burak.celik@example.com",   "phone": "05552223344", "city": "İzmir",     "segment": "standard", "registered_at": datetime(2026,  4,  1), "total_orders": 2,  "lifetime_value":  480.0},
    {"customer_id": "C010", "name": "Zeynep Kaya",        "email": "zeynep.kaya@example.com",   "phone": "05554445566", "city": "Antalya",   "segment": "premium",  "registered_at": datetime(2026,  1, 28), "total_orders": 6,  "lifetime_value": 1980.0},
]

PRODUCTS = [
    {"product_id": "P001", "name": "Classic Vanilla Macaroon",    "category": "Klasik",   "price": 45.0,  "cost": 18.0, "stock": 120, "min_stock": 30, "is_active": True,  "rating": 4.7, "review_count": 142},
    {"product_id": "P002", "name": "Pistachio Dream",             "category": "Premium",  "price": 55.0,  "cost": 22.0, "stock":  80, "min_stock": 20, "is_active": True,  "rating": 4.9, "review_count":  98},
    {"product_id": "P003", "name": "Chocolate Hazelnut",          "category": "Klasik",   "price": 48.0,  "cost": 19.0, "stock":  95, "min_stock": 25, "is_active": True,  "rating": 4.6, "review_count": 210},
    {"product_id": "P004", "name": "Rose Raspberry",              "category": "Sezonluk", "price": 60.0,  "cost": 24.0, "stock":  40, "min_stock": 15, "is_active": True,  "rating": 4.8, "review_count":  67},
    {"product_id": "P005", "name": "Salted Caramel",              "category": "Premium",  "price": 58.0,  "cost": 23.0, "stock":   0, "min_stock": 20, "is_active": False, "rating": 4.5, "review_count":  54},
    {"product_id": "P006", "name": "Lemon Lavender",              "category": "Sezonluk", "price": 62.0,  "cost": 25.0, "stock":  35, "min_stock": 10, "is_active": True,  "rating": 4.4, "review_count":  31},
    {"product_id": "P007", "name": "Matcha Green Tea",            "category": "Premium",  "price": 65.0,  "cost": 26.0, "stock":  60, "min_stock": 15, "is_active": True,  "rating": 4.8, "review_count":  89},
    {"product_id": "P008", "name": "Strawberry Cheesecake",       "category": "Klasik",   "price": 50.0,  "cost": 20.0, "stock":  75, "min_stock": 20, "is_active": True,  "rating": 4.7, "review_count": 175},
    {"product_id": "P009", "name": "Espresso Dark Chocolate",     "category": "Premium",  "price": 68.0,  "cost": 27.0, "stock":  45, "min_stock": 15, "is_active": True,  "rating": 4.9, "review_count":  62},
    {"product_id": "P010", "name": "Coconut Mango",               "category": "Sezonluk", "price": 58.0,  "cost": 23.0, "stock":  20, "min_stock": 10, "is_active": True,  "rating": 4.3, "review_count":  28},
]

# ---------------------------------------------------------------------------
# Dinamik veri üretimi
# ---------------------------------------------------------------------------

def _make_orders(rng: Random) -> list[dict]:
    """120 günlük sipariş geçmişi üretir — gerçekçi sezon patikası ile."""
    orders = []
    base_date = datetime(2026, 3, 1)
    order_num = 1001

    daily_demand = {  # noqa: F841
        "P001": 3, "P002": 2, "P003": 4, "P008": 3,
        "P004": 1, "P006": 1, "P010": 1,
        "P007": 2, "P009": 1,
    }

    for day_offset in range(120):
        date = base_date + timedelta(days=day_offset)
        # Hafta sonu artışı (x1.5) + ramazan/yaz sezonu bonus
        is_weekend = date.weekday() >= 5
        season_bonus = 1.4 if 60 <= day_offset <= 90 else 1.0  # yaz sezonu
        day_mult = (1.5 if is_weekend else 1.0) * season_bonus

        # Günde 1-6 sipariş
        num_orders = max(1, round(rng.gauss(3, 1.2) * day_mult))
        for _ in range(num_orders):
            customer = rng.choice(CUSTOMERS)
            # Sipariş başına 1-4 farklı ürün
            num_items = rng.randint(1, 4)
            available_products = [p for p in PRODUCTS if p["is_active"] and p["stock"] > 0]
            if not available_products:
                continue
            items_list = rng.sample(available_products, min(num_items, len(available_products)))

            items = []
            for prod in items_list:
                qty = rng.randint(2, 12)
                items.append({
                    "product_id": prod["product_id"],
                    "product_name": prod["name"],
                    "category": prod["category"],
                    "quantity": qty,
                    "unit_price": prod["price"],
                    "subtotal": round(qty * prod["price"], 2),
                })

            total = round(sum(i["subtotal"] for i in items), 2)
            discount = 0.0
            if customer["segment"] == "vip":
                discount = round(total * 0.10, 2)
            elif customer["segment"] == "premium":
                discount = round(total * 0.05, 2)

            channel = rng.choice(["online", "online", "online", "store", "store"])
            status_choices = ["delivered"] * 7 + ["processing"] * 2 + ["cancelled"] * 1
            status = rng.choice(status_choices)

            orders.append({
                "order_id":       f"O{order_num}",
                "customer_id":    customer["customer_id"],
                "order_date":     date + timedelta(hours=rng.randint(8, 22), minutes=rng.randint(0, 59)),
                "items":          items,
                "total_amount":   total,
                "discount":       discount,
                "net_amount":     round(total - discount, 2),
                "status":         status,
                "channel":        channel,
                "city":           customer["city"],
                "payment_method": rng.choice(["credit_card", "credit_card", "debit_card", "cash"]),
            })
            order_num += 1

    return orders


def _make_inventory(rng: Random) -> list[dict]:
    """Stok hareket kayıtları (giriş/çıkış)."""
    movements = []
    base_date = datetime(2026, 3, 1)
    for product in PRODUCTS:
        # Her ürün için 4-8 stok hareketi
        for i in range(rng.randint(4, 8)):
            mv_date = base_date + timedelta(days=rng.randint(0, 115))
            mv_type = rng.choice(["purchase", "purchase", "return", "adjustment"])
            qty = rng.randint(20, 150) if mv_type == "purchase" else rng.randint(1, 10)
            movements.append({
                "product_id":   product["product_id"],
                "product_name": product["name"],
                "category":     product["category"],
                "movement_type": mv_type,
                "quantity":     qty if mv_type != "adjustment" else rng.choice([-5, -3, 5, 3]),
                "unit_cost":    product["cost"],
                "total_cost":   round(qty * product["cost"], 2),
                "date":         mv_date,
                "warehouse":    rng.choice(["İstanbul-Merkez", "Ankara-Depo", "İzmir-Şube"]),
                "notes":        None,
            })
    return movements


def _make_campaigns(rng: Random) -> list[dict]:
    """Pazarlama kampanyası verileri."""
    campaigns = [
        {
            "campaign_id":   "CAM001",
            "name":          "Yaz Festivali %10 İndirim",
            "type":          "discount",
            "target_segment": "all",
            "start_date":    datetime(2026, 6, 1),
            "end_date":      datetime(2026, 6, 30),
            "discount_rate": 0.10,
            "budget":        5000.0,
            "impressions":   12400,
            "clicks":         3100,
            "conversions":     420,
            "revenue_generated": 18900.0,
            "status":        "completed",
        },
        {
            "campaign_id":   "CAM002",
            "name":          "Premium Üye Özel Pistachio Set",
            "type":          "bundle",
            "target_segment": "premium",
            "start_date":    datetime(2026, 5, 15),
            "end_date":      datetime(2026, 5, 31),
            "discount_rate": 0.05,
            "budget":        2000.0,
            "impressions":    4800,
            "clicks":         1200,
            "conversions":     180,
            "revenue_generated": 9900.0,
            "status":        "completed",
        },
        {
            "campaign_id":   "CAM003",
            "name":          "Ramazan Özel Kutusu",
            "type":          "seasonal",
            "target_segment": "all",
            "start_date":    datetime(2026, 3, 20),
            "end_date":      datetime(2026, 4, 20),
            "discount_rate": 0.0,
            "budget":        3500.0,
            "impressions":   18700,
            "clicks":         5600,
            "conversions":     830,
            "revenue_generated": 37350.0,
            "status":        "completed",
        },
        {
            "campaign_id":   "CAM004",
            "name":          "VIP Özel Matcha Lansmanı",
            "type":          "launch",
            "target_segment": "vip",
            "start_date":    datetime(2026, 7, 1),
            "end_date":      datetime(2026, 7, 31),
            "discount_rate": 0.15,
            "budget":        1500.0,
            "impressions":    2200,
            "clicks":          880,
            "conversions":     210,
            "revenue_generated": 13650.0,
            "status":        "active",
        },
        {
            "campaign_id":   "CAM005",
            "name":          "Sonbahar Yeni Ürün Tanıtımı",
            "type":          "awareness",
            "target_segment": "standard",
            "start_date":    datetime(2026, 9, 1),
            "end_date":      datetime(2026, 9, 30),
            "discount_rate": 0.0,
            "budget":        4000.0,
            "impressions":       0,
            "clicks":            0,
            "conversions":       0,
            "revenue_generated": 0.0,
            "status":        "planned",
        },
    ]
    return campaigns


# ---------------------------------------------------------------------------
# Seed fonksiyonu
# ---------------------------------------------------------------------------

def seed_database(uri: str = MONGODB_URI) -> None:
    rng = Random(42)  # tekrarlanabilir veri için sabit seed

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db_name = uri.rsplit("/", 1)[-1].split("?")[0]
    db = client[db_name]

    print(f"MongoDB: {uri}")
    print(f"Veritabanı: {db_name}\n")

    # Koleksiyon verileri
    orders     = _make_orders(rng)
    inventory  = _make_inventory(rng)
    campaigns  = _make_campaigns(rng)

    collections: dict[str, list] = {
        "customers":  CUSTOMERS,
        "products":   PRODUCTS,
        "orders":     orders,
        "inventory":  inventory,
        "campaigns":  campaigns,
    }

    for name, documents in collections.items():
        db[name].drop()
        result = db[name].insert_many(documents)
        print(f"  ✓ {name:12s}: {len(result.inserted_ids):4d} belge eklendi")

    # Yararlı index'ler
    db["orders"].create_index([("order_date", ASCENDING)])
    db["orders"].create_index([("customer_id", ASCENDING)])
    db["orders"].create_index([("status", ASCENDING)])
    db["inventory"].create_index([("product_id", ASCENDING)])
    db["inventory"].create_index([("date", ASCENDING)])
    db["campaigns"].create_index([("status", ASCENDING)])

    client.close()

    total = sum(len(d) for d in collections.values())
    print(f"\n✅  Toplam {total} belge başarıyla mydb'ye yüklendi.")
    print("\nÖrnek sorgular:")
    print("  db.orders.countDocuments({status: 'delivered'})")
    print("  db.orders.aggregate([{$group:{_id:'$channel', total:{$sum:'$net_amount'}}}])")
    print("  db.campaigns.find({status:'active'})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MongoDB mydb seed scripti")
    parser.add_argument(
        "--uri",
        default=MONGODB_URI,
        help=f"MongoDB bağlantı URI (varsayılan: {MONGODB_URI})",
    )
    args = parser.parse_args()
    seed_database(args.uri)
