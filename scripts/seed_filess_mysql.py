"""Filess.io MySQL'e demo seed data yükler."""
from sqlalchemy import create_engine, text

MYSQL_URL = (
    "mysql+pymysql://yztamysql_materialto:86770947145b013530230bdaa8686c7f1b34f34a"
    "@907wvf.h.filess.io:61002/yztamysql_materialto"
)

engine = create_engine(MYSQL_URL)

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS orders"))
    conn.execute(text("DROP TABLE IF EXISTS customers"))

    conn.execute(text("""
        CREATE TABLE customers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            city VARCHAR(100),
            age INT,
            segment VARCHAR(50)
        )
    """))
    conn.execute(text("""
        INSERT INTO customers (name, city, age, segment) VALUES
        ('Ayse Yilmaz',  'Ankara',   34, 'premium'),
        ('Mehmet Kaya',  'Istanbul', 28, 'standard'),
        ('Zeynep Demir', 'Izmir',    NULL, 'premium'),
        ('Ali Celik',    'Ankara',   45, 'vip'),
        ('Fatma Sahin',  'Bursa',    32, 'standard')
    """))

    conn.execute(text("""
        CREATE TABLE orders (
            id INT PRIMARY KEY AUTO_INCREMENT,
            customer_id INT NOT NULL,
            product VARCHAR(100),
            amount DOUBLE,
            order_date DATE,
            status VARCHAR(50),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """))
    conn.execute(text("""
        INSERT INTO orders (customer_id, product, amount, order_date, status) VALUES
        (1, 'Laptop',    15000.0, '2026-06-10', 'delivered'),
        (1, 'Mouse',       300.0, '2026-06-15', 'delivered'),
        (2, 'Klavye',      750.0, '2026-06-20', 'delivered'),
        (3, 'Monitor',    4200.0, '2026-07-01', 'processing'),
        (4, 'Laptop',    16500.0, '2026-07-05', 'delivered'),
        (5, 'Kulaklik',   1200.0, '2026-07-10', 'delivered')
    """))

    print("customers : 5 satir")
    print("orders    : 6 satir")
    print("SEED_OK")

engine.dispose()
