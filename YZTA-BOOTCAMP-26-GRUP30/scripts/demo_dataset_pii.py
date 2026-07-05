from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.security.anonymizer import PIIAnonymizer


df = pd.DataFrame(
    {
        "customer_name": [
            "Şehmus Kaya",
            "Nimet Asude Yalçın",
            "Ahmet Yılmaz",
        ],
        "email": [
            "sehmus@example.com",
            "nimet@example.com",
            "ahmet.yilmaz@example.com",
        ],
        "telefon": [
            "05551234567",
            "+905559876543",
            "05551112233",
        ],
        "tc_no": [
            "10000000146",
            "10000000146",
            "10000000146",
        ],
        "total_order": [
            1200,
            2500,
            900,
        ],
        "note": [
            "Müşteri tekrar aranacak: 05551234567",
            "Mail ile bilgilendirilecek: nimet@example.com",
            "Kişisel bilgi yok, sadece kampanya bekliyor",
        ],
    }
)

anonymizer = PIIAnonymizer()
masked_df = anonymizer.anonymize_dataframe(df)

print("ORİJİNAL DATASET")
print(df)

print("\nMASKELENMİŞ DATASET")
print(masked_df)

output_path = PROJECT_ROOT / "data" / "output" / "sample_customers_masked.csv"
masked_df.to_csv(output_path, index=False)

print(f"\nMaskelenmiş CSV oluşturuldu: {output_path}")