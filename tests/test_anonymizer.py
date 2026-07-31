from types import SimpleNamespace

import pandas as pd
import pytest

from src.security.anonymizer import PIIAnonymizer


@pytest.fixture(scope="module")
def anonymizer():
    return PIIAnonymizer()


def test_email_is_masked_in_text(anonymizer):
    text = "Kullanıcının mail adresi test.user@example.com"
    result = anonymizer.anonymize_text(text)

    assert "test.user@example.com" not in result
    assert "<EMAIL>" in result


def test_phone_is_masked_in_text(anonymizer):
    text = "Telefon numarası 05551234567"
    result = anonymizer.anonymize_text(text)

    assert "05551234567" not in result
    assert "<PHONE>" in result


def test_phone_with_country_code_is_masked(anonymizer):
    text = "Kullanıcı telefonu +905551234567"
    result = anonymizer.anonymize_text(text)

    assert "+905551234567" not in result
    assert "<PHONE>" in result


def test_tckn_is_masked_in_text(anonymizer):
    text = "TCKN numarası 10000000146"
    result = anonymizer.anonymize_text(text)

    assert "10000000146" not in result
    assert "<TCKN>" in result


def test_invalid_tckn_is_not_masked(anonymizer):
    text = "Bu geçersiz kimlik numarası 12345678901"
    result = anonymizer.anonymize_text(text)

    assert "12345678901" in result
    assert "<TCKN>" not in result


def test_dict_is_masked(anonymizer):
    data = {
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "05551234567",
        "order_total": 1200,
    }

    result = anonymizer.anonymize_dict(data)

    assert "john@example.com" not in str(result)
    assert "05551234567" not in str(result)
    assert result["order_total"] == 1200


def test_nested_dict_is_masked(anonymizer):
    data = {
        "customer": {
            "email": "nested.user@example.com",
            "phone": "05551234567",
        },
        "status": "active",
    }

    result = anonymizer.anonymize_dict(data)

    assert "nested.user@example.com" not in str(result)
    assert "05551234567" not in str(result)
    assert result["status"] == "active"


def test_dataframe_column_based_masking(anonymizer):
    df = pd.DataFrame(
        {
            "customer_name": ["Şehmus Kaya", "Nimet Asude Yalçın"],
            "email": ["sehmus@example.com", "nimet@example.com"],
            "telefon": ["05551234567", "05559876543"],
            "tc_no": ["10000000146", "10000000146"],
            "total_order": [1200, 2500],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert result.loc[0, "customer_name"] == "Customer-001"
    assert result.loc[1, "customer_name"] == "Customer-002"

    assert result.loc[0, "email"] == "<EMAIL>"
    assert result.loc[1, "email"] == "<EMAIL>"

    assert result.loc[0, "telefon"] == "<PHONE>"
    assert result.loc[1, "telefon"] == "<PHONE>"

    assert result.loc[0, "tc_no"] == "<TCKN>"
    assert result.loc[1, "tc_no"] == "<TCKN>"

    assert result.loc[0, "total_order"] == 1200
    assert result.loc[1, "total_order"] == 2500


def test_dataframe_turkish_column_names_are_detected(anonymizer):
    df = pd.DataFrame(
        {
            "Müşteri Adı": ["Ayşe Demir"],
            "E Posta": ["ayse@example.com"],
            "Telefon Numarası": ["05551234567"],
            "TC Kimlik Numarası": ["10000000146"],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert result.loc[0, "Müşteri Adı"] == "Customer-001"
    assert result.loc[0, "E Posta"] == "<EMAIL>"
    assert result.loc[0, "Telefon Numarası"] == "<PHONE>"
    assert result.loc[0, "TC Kimlik Numarası"] == "<TCKN>"


def test_dataframe_free_text_note_masks_email_and_phone(anonymizer):
    df = pd.DataFrame(
        {
            "note": [
                "Müşteri tekrar aranacak: 05551234567",
                "Mail ile bilgilendirilecek: nimet@example.com",
            ],
            "total_order": [1200, 2500],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert "05551234567" not in result.loc[0, "note"]
    assert "<PHONE>" in result.loc[0, "note"]

    assert "nimet@example.com" not in result.loc[1, "note"]
    assert "<EMAIL>" in result.loc[1, "note"]

    assert result.loc[0, "total_order"] == 1200
    assert result.loc[1, "total_order"] == 2500


def test_dataframe_preserves_missing_values(anonymizer):
    df = pd.DataFrame(
        {
            "email": ["test@example.com", None],
            "telefon": ["05551234567", None],
            "total_order": [1000, 2000],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert result.loc[0, "email"] == "<EMAIL>"
    assert pd.isna(result.loc[1, "email"])

    assert result.loc[0, "telefon"] == "<PHONE>"
    assert pd.isna(result.loc[1, "telefon"])

    assert result.loc[0, "total_order"] == 1000
    assert result.loc[1, "total_order"] == 2000


def test_original_dataframe_is_not_modified(anonymizer):
    df = pd.DataFrame(
        {
            "email": ["original@example.com"],
            "total_order": [1500],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert df.loc[0, "email"] == "original@example.com"
    assert result.loc[0, "email"] == "<EMAIL>"


def test_dict_masks_turkish_name_by_key(anonymizer):
    data = {
        "name": "Nimet Asude Yalçın",
        "profil": {
            "Müşteri Adı": "Ayşe Demir",
            "status": "active",
        },
    }

    result = anonymizer.anonymize_dict(data)

    assert result["name"] == "Customer-001"
    assert result["profil"]["Müşteri Adı"] == "Customer-002"
    assert result["profil"]["status"] == "active"


def test_dict_masks_pii_inside_list_of_dicts(anonymizer):
    data = {
        "customers": [
            {
                "name": "Nimet Asude Yalçın",
                "email": "nimet@example.com",
                "telefon": "05551234567",
                "tc_no": "10000000146",
                "total_order": 2500,
            },
            {
                "name": "Ayşe Demir",
                "email": "ayse@example.com",
                "telefon": "+905559876543",
                "tc_no": "10000000146",
                "total_order": 1200,
            },
        ]
    }

    result = anonymizer.anonymize_dict(data)

    assert result["customers"][0]["name"] == "Customer-001"
    assert result["customers"][0]["email"] == "<EMAIL>"
    assert result["customers"][0]["telefon"] == "<PHONE>"
    assert result["customers"][0]["tc_no"] == "<TCKN>"
    assert result["customers"][0]["total_order"] == 2500

    assert result["customers"][1]["name"] == "Customer-002"
    assert result["customers"][1]["email"] == "<EMAIL>"
    assert result["customers"][1]["telefon"] == "<PHONE>"
    assert result["customers"][1]["tc_no"] == "<TCKN>"
    assert result["customers"][1]["total_order"] == 1200

    result_text = str(result)

    assert "Nimet Asude Yalçın" not in result_text
    assert "Ayşe Demir" not in result_text
    assert "nimet@example.com" not in result_text
    assert "ayse@example.com" not in result_text
    assert "05551234567" not in result_text
    assert "+905559876543" not in result_text
    assert "10000000146" not in result_text


def test_dataframe_reuses_customer_alias_for_same_person(anonymizer):
    df = pd.DataFrame(
        {
            "customer_name": [
                "Ayşe Demir",
                "Mehmet Kaya",
                "  AYŞE   DEMİR  ",
            ],
            "total_order": [1200, 2500, 1800],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert result["customer_name"].tolist() == [
        "Customer-001",
        "Customer-002",
        "Customer-001",
    ]
    assert "Ayşe Demir" not in result.to_string()
    assert "Mehmet Kaya" not in result.to_string()


def test_all_structured_person_fields_use_customer_aliases(anonymizer):
    data = {
        "customer_name": "Ayşe Demir",
        "employee_name": "Mehmet Kaya",
        "patient_name": "Deniz Şahin",
        "supplier_contact_name": "Derya Yılmaz",
        "authorized_person": "Ege Öztürk",
        "user_name": "Nimet Yalçın",
        "name": "John Smith",
    }

    result = anonymizer.anonymize_dict(data)

    assert result == {
        "customer_name": "Customer-001",
        "employee_name": "Customer-002",
        "patient_name": "Customer-003",
        "supplier_contact_name": "Customer-004",
        "authorized_person": "Customer-005",
        "user_name": "Customer-006",
        "name": "Customer-007",
    }


def test_nested_customer_container_passes_role_to_name_field(anonymizer):
    data = {
        "customers": [
            {"name": "Ayşe Demir", "total_order": 1200},
            {"name": "Ayşe Demir", "total_order": 2500},
            {"name": "Mehmet Kaya", "total_order": 1800},
        ]
    }

    result = anonymizer.anonymize_dict(data)

    assert [customer["name"] for customer in result["customers"]] == [
        "Customer-001",
        "Customer-001",
        "Customer-002",
    ]


def test_alias_sequence_resets_for_each_public_call(anonymizer):
    first_result = anonymizer.anonymize_dict({"customer_name": "Ayşe Demir"})
    second_result = anonymizer.anonymize_dict({"customer_name": "Mehmet Kaya"})

    assert first_result["customer_name"] == "Customer-001"
    assert second_result["customer_name"] == "Customer-001"


def test_customer_aliases_are_preserved_when_chart_rows_are_masked_again(
    anonymizer,
):
    rows = [
        {"customer_name": "Customer-001", "total_order": 7500},
        {"customer_name": "Customer-002", "total_order": 500},
    ]

    result = [anonymizer.anonymize_dict(row) for row in rows]

    assert result == rows


def test_dataframe_pseudonymization_is_idempotent(anonymizer):
    df = pd.DataFrame(
        {
            "customer_name": ["Ayşe Demir", "Mehmet Kaya"],
            "total_order": [7500, 500],
        }
    )

    first_result = anonymizer.anonymize_dataframe(df)
    second_result = anonymizer.anonymize_dataframe(first_result)

    pd.testing.assert_frame_equal(first_result, second_result)


def test_person_column_preserves_missing_and_blank_values(anonymizer):
    df = pd.DataFrame(
        {
            "customer_name": ["Ayşe Demir", None, ""],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert result.loc[0, "customer_name"] == "Customer-001"
    assert pd.isna(result.loc[1, "customer_name"])
    assert result.loc[2, "customer_name"] == ""


def test_free_text_people_receive_unique_and_reusable_aliases(
    anonymizer,
    monkeypatch,
):
    text = "John Smith ve Jane Doe, sonra John Smith"
    fake_results = [
        SimpleNamespace(
            entity_type="PERSON",
            start=0,
            end=10,
            score=0.90,
        ),
        SimpleNamespace(
            entity_type="PERSON",
            start=14,
            end=22,
            score=0.90,
        ),
        SimpleNamespace(
            entity_type="PERSON",
            start=30,
            end=40,
            score=0.90,
        ),
    ]
    monkeypatch.setattr(
        anonymizer.analyzer,
        "analyze",
        lambda **_: fake_results,
    )

    result = anonymizer.anonymize_text(text)

    assert result == ("Customer-001 ve Customer-002, sonra Customer-001")
    assert "John Smith" not in result
    assert "Jane Doe" not in result


def test_email_detection_wins_over_overlapping_person_detection(
    anonymizer,
    monkeypatch,
):
    text = "john@example.com"
    fake_results = [
        SimpleNamespace(
            entity_type="PERSON",
            start=0,
            end=len(text),
            score=0.99,
        ),
        SimpleNamespace(
            entity_type="EMAIL_ADDRESS",
            start=0,
            end=len(text),
            score=0.80,
        ),
    ]
    monkeypatch.setattr(
        anonymizer.analyzer,
        "analyze",
        lambda **_: fake_results,
    )

    result = anonymizer.anonymize_text(text)

    assert result == "<EMAIL>"


@pytest.mark.parametrize(
    "phone_number",
    [
        "(0555) 123 45 67",
        "0555-123-45-67",
        "+90 (555) 123-45-67",
    ],
)
def test_additional_phone_formats_are_masked(
    anonymizer,
    phone_number,
):
    text = f"Müşteri telefonu: {phone_number}"

    result = anonymizer.anonymize_text(text)

    assert phone_number not in result
    assert "<PHONE>" in result


@pytest.mark.parametrize(
    ("field_name", "location"),
    [
        ("city", "İzmir"),
        ("şehir", "İzmir"),
        ("customer_city", "Ankara"),
        ("shipping_city", "İstanbul"),
        ("province", "Bursa"),
        ("il", "İzmir"),
        ("district", "Kadıköy"),
        ("ilçe", "Çankaya"),
        ("country", "Türkiye"),
        ("ülke", "Türkiye"),
        ("region", "Ege"),
        ("bölge", "Marmara"),
    ],
)
def test_dict_preserves_structured_location_values(
    anonymizer,
    field_name,
    location,
):
    result = anonymizer.anonymize_dict({field_name: location})

    assert result[field_name] == location
    assert "<PERSON>" not in result[field_name]


def test_dict_preserves_city_while_masking_other_pii(anonymizer):
    data = {
        "city": "İzmir",
        "customer_name": "Ayşe Demir",
        "email": "ayse@example.com",
        "phone": "05551234567",
        "tc_no": "10000000146",
    }

    result = anonymizer.anonymize_dict(data)

    assert result["city"] == "İzmir"
    assert result["customer_name"] == "Customer-001"
    assert result["email"] == "<EMAIL>"
    assert result["phone"] == "<PHONE>"
    assert result["tc_no"] == "<TCKN>"


def test_dataframe_preserves_city_chart_labels(anonymizer):
    df = pd.DataFrame(
        {
            "city": ["Ankara", "İstanbul", "İzmir", "Bursa"],
            "total_orders": [120, 180, 95, 140],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert result["city"].tolist() == [
        "Ankara",
        "İstanbul",
        "İzmir",
        "Bursa",
    ]
    assert "<PERSON>" not in result["city"].tolist()
    assert result["total_orders"].tolist() == [120, 180, 95, 140]


def test_dataframe_preserves_location_and_masks_pii_columns(anonymizer):
    df = pd.DataFrame(
        {
            "şehir": ["İzmir"],
            "Müşteri Adı": ["Ayşe Demir"],
            "E Posta": ["ayse@example.com"],
            "Telefon Numarası": ["05551234567"],
            "TC Kimlik Numarası": ["10000000146"],
            "Adres": ["Örnek Mahallesi No: 10"],
        }
    )

    result = anonymizer.anonymize_dataframe(df)

    assert result.loc[0, "şehir"] == "İzmir"
    assert result.loc[0, "Müşteri Adı"] == "Customer-001"
    assert result.loc[0, "E Posta"] == "<EMAIL>"
    assert result.loc[0, "Telefon Numarası"] == "<PHONE>"
    assert result.loc[0, "TC Kimlik Numarası"] == "<TCKN>"
    assert result.loc[0, "Adres"] == "<ADDRESS>"


def test_location_field_still_masks_non_person_pii(anonymizer):
    data = {"city": ("İzmir test.user@example.com 05551234567 10000000146")}

    result = anonymizer.anonymize_dict(data)
    city_value = result["city"]

    assert "İzmir" in city_value
    assert "test.user@example.com" not in city_value
    assert "05551234567" not in city_value
    assert "10000000146" not in city_value
    assert "<EMAIL>" in city_value
    assert "<PHONE>" in city_value
    assert "<TCKN>" in city_value


def test_mask_person_false_only_disables_person_detection(anonymizer):
    text = "İzmir test.user@example.com 05551234567"

    result = anonymizer.anonymize_text(text, mask_person=False)

    assert "İzmir" in result
    assert "<PERSON>" not in result
    assert "test.user@example.com" not in result
    assert "05551234567" not in result
    assert "<EMAIL>" in result
    assert "<PHONE>" in result
