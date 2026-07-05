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

    assert result.loc[0, "customer_name"] == "<PERSON>"
    assert result.loc[1, "customer_name"] == "<PERSON>"

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

    assert result.loc[0, "Müşteri Adı"] == "<PERSON>"
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