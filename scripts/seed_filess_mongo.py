"""Filess.io MongoDB'ye demo seed data yükler."""
from datetime import datetime
from pymongo import MongoClient

MONGO_URI = (
    "mongodb://yztamongo_sheapartat:0a6e58e0ff39fca24b8a60766ed08049c18eddf8"
    "@btvmex.h.filess.io:27018/yztamongo_sheapartat"
)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client["yztamongo_sheapartat"]

# Customers
db["customers"].drop()
db["customers"].insert_many([
    {"customer_id": "C001", "name": "Elif Keskin",  "city": "Istanbul", "segment": "premium",  "total_orders": 8,  "lifetime_value": 3240.0},
    {"customer_id": "C002", "name": "Murat Sahin",  "city": "Istanbul", "segment": "vip",      "total_orders": 14, "lifetime_value": 6720.0},
    {"customer_id": "C003", "name": "Ayse Yildiz",  "city": "Ankara",   "segment": "vip",      "total_orders": 18, "lifetime_value": 8460.0},
    {"customer_id": "C004", "name": "Kerem Ozturk", "city": "Istanbul", "segment": "premium",  "total_orders": 7,  "lifetime_value": 2940.0},
    {"customer_id": "C005", "name": "Zeynep Kaya",  "city": "Antalya",  "segment": "premium",  "total_orders": 6,  "lifetime_value": 1980.0},
])

# Products
db["products"].drop()
db["products"].insert_many([
    {"product_id": "P001", "name": "Classic Vanilla Macaroon", "category": "Klasik",   "price": 45.0, "stock": 120},
    {"product_id": "P002", "name": "Pistachio Dream",          "category": "Premium",  "price": 55.0, "stock": 80},
    {"product_id": "P003", "name": "Matcha Green Tea",         "category": "Premium",  "price": 65.0, "stock": 60},
    {"product_id": "P004", "name": "Rose Raspberry",           "category": "Sezonluk", "price": 60.0, "stock": 40},
    {"product_id": "P005", "name": "Espresso Dark Chocolate",  "category": "Premium",  "price": 68.0, "stock": 45},
])

# Orders
db["orders"].drop()
db["orders"].insert_many([
    {"order_id": "O001", "customer_id": "C001", "product": "Pistachio Dream",      "amount": 550.0, "order_date": datetime(2026, 6, 15), "status": "delivered", "channel": "online"},
    {"order_id": "O002", "customer_id": "C001", "product": "Matcha Green Tea",     "amount": 390.0, "order_date": datetime(2026, 7,  1), "status": "delivered", "channel": "online"},
    {"order_id": "O003", "customer_id": "C002", "product": "Classic Vanilla",      "amount": 270.0, "order_date": datetime(2026, 6, 20), "status": "delivered", "channel": "store"},
    {"order_id": "O004", "customer_id": "C003", "product": "Espresso Chocolate",   "amount": 680.0, "order_date": datetime(2026, 7,  5), "status": "delivered", "channel": "online"},
    {"order_id": "O005", "customer_id": "C004", "product": "Rose Raspberry",       "amount": 480.0, "order_date": datetime(2026, 6, 28), "status": "processing","channel": "online"},
    {"order_id": "O006", "customer_id": "C005", "product": "Pistachio Dream",      "amount": 330.0, "order_date": datetime(2026, 7, 10), "status": "delivered", "channel": "store"},
])

print("customers : 5 belge")
print("products  : 5 belge")
print("orders    : 6 belge")
print("SEED_OK")

client.close()
