"""
MongoDB'ye örnek dataset yükler (macaroon market senaryosu).

Çalıştır:  python scripts/seed_mongodb.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(PROJECT_ROOT / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/mydb")

CUSTOMERS = [
    {
        "customer_id": "C001",
        "name": "Elif Keskin",
        "email": "elif.keskin@example.com",
        "phone": "05551234567",
        "city": "Istanbul",
        "segment": "premium",
        "registered_at": datetime(2025, 11, 10),
    },
    {
        "customer_id": "C002",
        "name": "Recep Atabey Demir",
        "email": "recep@example.com",
        "phone": "05559876543",
        "city": "Ankara",
        "segment": "standard",
        "registered_at": datetime(2025, 12, 5),
    },
    {
        "customer_id": "C003",
        "name": "Nimet Asude Yalçın",
        "email": "nimet@example.com",
        "phone": "05551112233",
        "city": "Sakarya",
        "segment": "premium",
        "registered_at": datetime(2026, 1, 15),
    },
    {
        "customer_id": "C004",
        "name": "Rida Doğrul",
        "email": "rida@example.com",
        "phone": "05550001122",
        "city": "Izmir",
        "segment": "standard",
        "registered_at": datetime(2026, 2, 20),
    },
]

PRODUCTS = [
    {
        "product_id": "P001",
        "name": "Classic Vanilla Macaroon",
        "category": "Klasik",
        "price": 45.0,
        "stock": 120,
        "is_active": True,
    },
    {
        "product_id": "P002",
        "name": "Pistachio Dream",
        "category": "Premium",
        "price": 55.0,
        "stock": 80,
        "is_active": True,
    },
    {
        "product_id": "P003",
        "name": "Chocolate Hazelnut",
        "category": "Klasik",
        "price": 48.0,
        "stock": 95,
        "is_active": True,
    },
    {
        "product_id": "P004",
        "name": "Rose Raspberry",
        "category": "Sezonluk",
        "price": 60.0,
        "stock": 40,
        "is_active": True,
    },
    {
        "product_id": "P005",
        "name": "Salted Caramel",
        "category": "Premium",
        "price": 58.0,
        "stock": 0,
        "is_active": False,
    },
]

ORDERS = [
    {
        "order_id": "O1001",
        "customer_id": "C001",
        "items": [
            {"product_id": "P001", "quantity": 6, "unit_price": 45.0},
            {"product_id": "P002", "quantity": 4, "unit_price": 55.0},
        ],
        "total_amount": 490.0,
        "status": "delivered",
        "channel": "online",
        "order_date": datetime(2026, 6, 12, 14, 30),
    },
    {
        "order_id": "O1002",
        "customer_id": "C002",
        "items": [{"product_id": "P003", "quantity": 12, "unit_price": 48.0}],
        "total_amount": 576.0,
        "status": "delivered",
        "channel": "store",
        "order_date": datetime(2026, 6, 18, 11, 0),
    },
    {
        "order_id": "O1003",
        "customer_id": "C003",
        "items": [
            {"product_id": "P004", "quantity": 8, "unit_price": 60.0},
            {"product_id": "P001", "quantity": 4, "unit_price": 45.0},
        ],
        "total_amount": 660.0,
        "status": "processing",
        "channel": "online",
        "order_date": datetime(2026, 7, 1, 9, 15),
    },
    {
        "order_id": "O1004",
        "customer_id": "C001",
        "items": [{"product_id": "P002", "quantity": 10, "unit_price": 55.0}],
        "total_amount": 550.0,
        "status": "delivered",
        "channel": "online",
        "order_date": datetime(2026, 7, 3, 16, 45),
    },
    {
        "order_id": "O1005",
        "customer_id": "C004",
        "items": [{"product_id": "P003", "quantity": 6, "unit_price": 48.0}],
        "total_amount": 288.0,
        "status": "cancelled",
        "channel": "online",
        "order_date": datetime(2026, 7, 4, 10, 0),
    },
]


def seed_database(uri: str = MONGODB_URI) -> None:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db_name = uri.rsplit("/", 1)[-1].split("?")[0]
    db = client[db_name]

    collections = {
        "customers": CUSTOMERS,
        "products": PRODUCTS,
        "orders": ORDERS,
    }

    print(f"MongoDB: {uri}")
    print(f"Veritabanı: {db_name}\n")

    for name, documents in collections.items():
        db[name].delete_many({})
        result = db[name].insert_many(documents)
        print(f"  {name}: {len(result.inserted_ids)} belge yüklendi")

    client.close()
    print("\nÖrnek dataset başarıyla eklendi.")


if __name__ == "__main__":
    seed_database()
