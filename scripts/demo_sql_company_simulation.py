from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3

import pandas as pd

from src.security.anonymizer import PIIAnonymizer


def create_company_database():
    """
    Gerçek bir şirket SQL veritabanını taklit eden küçük bir SQLite veritabanı oluşturur.

    Not:
    SQLite burada sadece test için kullanılıyor.
    Gerçek projede PostgreSQL/MySQL connector aynı mantıkla DataFrame döndürecek.
    """

    connection = sqlite3.connect(":memory:")

    customers = pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4],
            "customer_name": [
                "John Smith",
                "Nimet Asude Yalçın",
                "Maria Garcia",
                "Şehmus Kaya",
            ],
            "email": [
                "john.smith@example.com",
                "nimet@example.com",
                "maria.garcia@example.com",
                "sehmus@example.com",
            ],
            "telefon": [
                "05551234567",
                "+905559876543",
                "05551112233",
                "05550001122",
            ],
            "tc_no": [
                "10000000146",
                "10000000146",
                "10000000146",
                "10000000146",
            ],
            "city": [
                "Istanbul",
                "Sakarya",
                "Madrid",
                "Diyarbakir",
            ],
        }
    )

    orders = pd.DataFrame(
        {
            "order_id": [101, 102, 103, 104],
            "customer_id": [1, 2, 3, 4],
            "category": [
                "Tekstil",
                "Elektronik",
                "Kozmetik",
                "Tekstil",
            ],
            "total_order": [1200, 2500, 1800, 900],
            "order_date": [
                "2026-07-01",
                "2026-07-02",
                "2026-07-03",
                "2026-07-04",
            ],
        }
    )

    support_notes = pd.DataFrame(
        {
            "note_id": [1, 2, 3, 4],
            "customer_id": [1, 2, 3, 4],
            "note": [
                "Müşteri tekrar aranacak: 05551234567",
                "Mail ile bilgilendirilecek: nimet@example.com",
                "Customer John Smith requested campaign details.",
                "Kişisel bilgi yok, sadece kampanya bekliyor.",
            ],
        }
    )

    customers.to_sql("customers", connection, index=False, if_exists="replace")
    orders.to_sql("orders", connection, index=False, if_exists="replace")
    support_notes.to_sql("support_notes", connection, index=False, if_exists="replace")

    return connection


def run_sql_query(connection):
    """
    Şirketin veritabanından gelecek örnek bir rapor sorgusunu simüle eder.
    """

    query = """
    SELECT
        c.customer_id,
        c.customer_name,
        c.email,
        c.telefon,
        c.tc_no,
        c.city,
        o.category,
        o.total_order,
        o.order_date,
        s.note
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    LEFT JOIN support_notes s ON c.customer_id = s.customer_id
    ORDER BY o.order_date;
    """

    return pd.read_sql_query(query, connection)


def assert_no_sensitive_data_leaked(masked_df):
    """
    Maskelenmiş DataFrame içinde açık kişisel veri kalıp kalmadığını kontrol eder.
    """

    masked_text = masked_df.to_string()

    sensitive_values = [
        "john.smith@example.com",
        "nimet@example.com",
        "maria.garcia@example.com",
        "sehmus@example.com",
        "05551234567",
        "+905559876543",
        "05551112233",
        "05550001122",
        "10000000146",
    ]

    for value in sensitive_values:
        assert value not in masked_text, f"Sızıntı var: {value}"

    assert "<EMAIL>" in masked_text
    assert "<PHONE>" in masked_text
    assert "<TCKN>" in masked_text
    assert "<PERSON>" in masked_text


def assert_business_data_is_preserved(original_df, masked_df):
    """
    İş verileri korunuyor mu kontrol eder.
    PII maskelensin ama sipariş tutarı, kategori, tarih gibi analiz için gerekli alanlar bozulmasın.
    """

    assert original_df["total_order"].tolist() == masked_df["total_order"].tolist()
    assert original_df["category"].tolist() == masked_df["category"].tolist()
    assert original_df["order_date"].tolist() == masked_df["order_date"].tolist()
    assert original_df["city"].tolist() == masked_df["city"].tolist()


if __name__ == "__main__":
    connection = create_company_database()

    original_df = run_sql_query(connection)

    print("ORİJİNAL SQL SONUCU")
    print(original_df)

    anonymizer = PIIAnonymizer()
    masked_df = anonymizer.anonymize_dataframe(original_df)

    print("\nMASKELENMİŞ SQL SONUCU")
    print(masked_df)

    assert_no_sensitive_data_leaked(masked_df)
    assert_business_data_is_preserved(original_df, masked_df)

    output_path = PROJECT_ROOT / "data" / "output" / "company_sql_masked_result.csv"
    masked_df.to_csv(output_path, index=False)

    print(f"Maskelenmiş çıktı kaydedildi: {output_path}")
    print("\nTest başarılı.")
    print("Kişisel veriler maskelendi, iş verileri korundu.")
    print("Maskelenmiş çıktı kaydedildi: company_sql_masked_result.csv")