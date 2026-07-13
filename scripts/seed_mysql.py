"""

MySQL 'demo' veritabanına örnek tablo ve veri ekler (tek seferlik).
Orchestrator'ı gerçek veriyle test edebilmek için kullanılır.

İçine bilerek eksik (NULL) ve uç (outlier) değerler kondu; böylece
Agent 2'nin (DataCleaningPipeline) yaptığı iş çıktıda görünür.

Çalıştır:  python -m scripts.seed_mysql
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

project_root = Path(__file__).resolve().parents[1]
load_dotenv(project_root / ".env")

# Seed işlemi YAZMA gerektirir; bu yüzden read-only connector yerine
# doğrudan kendi bağlantımızı kuruyoruz.
MYSQL_URL = os.getenv("MYSQL_URL", "mysql+pymysql://root:test@localhost:3306/demo")


def seed() -> None:
    engine = create_engine(MYSQL_URL)
    with engine.begin() as conn:
        # Tekrar çalıştırılabilir olsun diye önce varsa sil (FK sırası önemli).
        conn.execute(text("DROP TABLE IF EXISTS orders"))
        conn.execute(text("DROP TABLE IF EXISTS customers"))

        # --- customers tablosu ---
        conn.execute(text("""
            CREATE TABLE customers (
                id   INT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                city VARCHAR(100),
                age  INT
            )
        """))

        # --- orders tablosu (customers'a FK ile bağlı) ---
        conn.execute(text("""
            CREATE TABLE orders (
                id          INT PRIMARY KEY,
                customer_id INT NOT NULL,
                product     VARCHAR(100),
                amount      DOUBLE,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """))

        # --- Örnek müşteriler ---
        # id=3 -> age NULL (eksik değer testi)
        # id=5 -> age 150 (uç değer / outlier testi)
        conn.execute(text("""
            INSERT INTO customers (id, name, city, age) VALUES
            (1, 'Ayse Yilmaz',  'Ankara',   34),
            (2, 'Mehmet Kaya',  'Istanbul', 28),
            (3, 'Zeynep Demir', 'Izmir',    NULL),
            (4, 'Ali Celik',    'Ankara',   45),
            (5, 'Fatma Sahin',  'Bursa',    150)
        """))

        # --- Örnek siparişler ---
        # id=6 -> amount 999999 (uç değer / outlier testi)
        conn.execute(text("""
            INSERT INTO orders (id, customer_id, product, amount) VALUES
            (1, 1, 'Laptop',    15000.0),
            (2, 1, 'Mouse',       300.0),
            (3, 2, 'Klavye',      750.0),
            (4, 3, 'Monitor',    4200.0),
            (5, 4, 'Laptop',    16500.0),
            (6, 5, 'Kulaklik', 999999.0)
        """))

    engine.dispose()
    print("✅ demo veritabani dolduruldu: customers (5 satir), orders (6 satir)")
    print("   - customers.age: 1 NULL, 1 outlier (150)")
    print("   - orders.amount: 1 outlier (999999)")


if __name__ == "__main__":
    seed()