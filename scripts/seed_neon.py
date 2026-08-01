"""Neon PostgreSQL'e demo seed data yükler."""
from sqlalchemy import create_engine, text

NEON_URL = (
    "postgresql+psycopg2://neondb_owner:npg_mwLqEhxBYF92"
    "@ep-falling-wave-a2us6mz5-pooler.eu-central-1.aws.neon.tech"
    "/neondb?sslmode=require"
)

engine = create_engine(NEON_URL)

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))

    conn.execute(text("""
        CREATE TABLE customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            city VARCHAR(100),
            segment VARCHAR(50),
            total_orders INT DEFAULT 0,
            lifetime_value NUMERIC(10,2) DEFAULT 0
        )
    """))
    conn.execute(text("""
        INSERT INTO customers (name, city, segment, total_orders, lifetime_value) VALUES
        ('Elif Keskin',  'Istanbul', 'premium',  8,  3240.00),
        ('Murat Sahin',  'Istanbul', 'vip',      14, 6720.00),
        ('Ayse Yildiz',  'Ankara',   'vip',      18, 8460.00),
        ('Kerem Ozturk', 'Istanbul', 'premium',  7,  2940.00),
        ('Zeynep Kaya',  'Antalya',  'premium',  6,  1980.00),
        ('Rida Dogrul',  'Izmir',    'standard', 2,   576.00),
        ('Selin Aydin',  'Bursa',    'standard', 1,   288.00)
    """))

    conn.execute(text("""
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            category VARCHAR(50),
            price NUMERIC(10,2),
            stock INT
        )
    """))
    conn.execute(text("""
        INSERT INTO products (name, category, price, stock) VALUES
        ('Classic Vanilla Macaroon', 'Klasik',   45.00, 120),
        ('Pistachio Dream',          'Premium',  55.00,  80),
        ('Chocolate Hazelnut',       'Klasik',   48.00,  95),
        ('Rose Raspberry',           'Sezonluk', 60.00,  40),
        ('Matcha Green Tea',         'Premium',  65.00,  60),
        ('Espresso Dark Chocolate',  'Premium',  68.00,  45)
    """))

    conn.execute(text("""
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            customer_id INT REFERENCES customers(id),
            product VARCHAR(100),
            amount NUMERIC(10,2),
            order_date DATE,
            status VARCHAR(50)
        )
    """))
    conn.execute(text("""
        INSERT INTO orders (customer_id, product, amount, order_date, status) VALUES
        (1, 'Pistachio Dream',       550.00, '2026-06-15', 'delivered'),
        (1, 'Matcha Green Tea',      390.00, '2026-07-01', 'delivered'),
        (2, 'Classic Vanilla',       270.00, '2026-06-20', 'delivered'),
        (3, 'Espresso Chocolate',    680.00, '2026-07-05', 'delivered'),
        (4, 'Rose Raspberry',        480.00, '2026-06-28', 'processing'),
        (5, 'Lemon Lavender',        310.00, '2026-07-10', 'delivered'),
        (6, 'Pistachio Dream',       220.00, '2026-07-12', 'delivered'),
        (7, 'Chocolate Hazelnut',    144.00, '2026-07-15', 'processing')
    """))

    print("customers : 7 satir")
    print("products  : 6 satir")
    print("orders    : 8 satir")
    print("SEED_OK")

engine.dispose()
