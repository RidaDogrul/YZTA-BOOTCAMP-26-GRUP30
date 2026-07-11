import re
from typing import Any

import pandas as pd
from pandas.api.types import is_string_dtype
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


class PIIAnonymizer:
    """
    Kişisel verileri maskeler.
    Örnek:
        Ahmet'in maili ahmet@example.com
    çıktısı:
        <PERSON>'in maili <EMAIL>
    """

    def __init__(self) -> None:
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_sm"},
            ],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine, supported_languages=["en"]
        )
        self.anonymizer = AnonymizerEngine()

    def anonymize_text(self, text: str) -> str:
        """Metin içindeki kişisel verileri maskeler."""
        if not text:
            return text

        # Presidio analizini çalıştır
        results = self.analyzer.analyze(
           text=text,
           language="en",
            entities=[
             "PERSON",
             "EMAIL_ADDRESS",
            ],
        )
        operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
        }
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        anonymized_text = anonymized_result.text

        # Ek regex kontrolleri
        anonymized_text = self._mask_email(anonymized_text)
        anonymized_text = self._mask_turkish_phone(anonymized_text)
        anonymized_text = self._mask_tckn(anonymized_text)
        return anonymized_text

    def anonymize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Dict içindeki kişisel verileri anahtar adlarını da dikkate alarak
        recursive biçimde maskeler.
        """
        return {
            key: self._anonymize_value(value, key_hint=str(key))
            for key, value in data.items()
        }

    def _anonymize_value(
        self,
        value: Any,
        key_hint: str | None = None,
    ) -> Any:
        """
        İç içe dict, list ve tuple yapılarını recursive olarak işler.

        key_hint verilmişse email, telefon, TCKN ve kişi adı gibi alanlar
        yalnızca metin analizine bağlı kalmadan kesin olarak maskelenir.
        """
        if isinstance(value, dict):
            return {
                key: self._anonymize_value(item, key_hint=str(key))
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                self._anonymize_value(item, key_hint=key_hint)
                for item in value
            ]

        if isinstance(value, tuple):
            return tuple(
                self._anonymize_value(item, key_hint=key_hint)
                for item in value
            )

        if key_hint is not None:
            pii_type = self._detect_pii_column_type(key_hint)

            if pii_type is not None:
                if value is None or (
                    not isinstance(value, str) and pd.isna(value)
                ):
                    return value

                return pii_type

        if isinstance(value, str):
            return self.anonymize_text(value)

        return value

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Pandas DataFrame içindeki PII verileri maskeler.

        Önce kolon adına bakar:
        - email/mail/e_posta -> <EMAIL>
        - phone/telefon/gsm -> <PHONE>
        - tckn/tc_no/tc_kimlik -> <TCKN>
        - name/ad_soyad/isim/customer_name -> <PERSON>

        Eğer kolon adı PII gibi görünmüyorsa, hücre metni içinde PII arar.
        """
        anonymized_df = df.copy()
        for column in anonymized_df.columns:
            pii_type = self._detect_pii_column_type(column)
            if pii_type:
                anonymized_df[column] = anonymized_df[column].apply(
                    lambda value: value if pd.isna(value) else pii_type
                )
            elif is_string_dtype(anonymized_df[column]):
                 anonymized_df[column] = anonymized_df[column].apply(
                  lambda value: self.anonymize_text(value)
                  if isinstance(value, str)
                  else value
                )
        return anonymized_df

    # Dahili yardımcı fonksiyonlar

    def _mask_email(self, text: str) -> str:
        """E-posta adreslerini regex ile maskeler."""
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        return re.sub(email_pattern, "<EMAIL>", text)

    def _mask_turkish_phone(self, text: str) -> str:
        """
        Türkiye cep telefonu numaralarını maskeler.

        Yakalanan örnekler:
        05551234567
        5551234567
        +905551234567
        00905551234567
        0 555 123 45 67
        """

        phone_pattern = (
            r"(?<!\d)"
            r"(?:(?:\+90|0090)[\s.-]*)?"
            r"\(?0?5\d{2}\)?"
            r"[\s.-]*"
            r"\d{3}"
            r"[\s.-]*"
            r"\d{2}"
            r"[\s.-]*"
            r"\d{2}"
            r"(?!\d)"
        )

        return re.sub(phone_pattern, "<PHONE>", text)

    def _mask_tckn(self, text: str) -> str:
        """11 haneli TCKN formatındaki sayıları maskeler."""
        possible_numbers = re.findall(r"\b[1-9][0-9]{10}\b", text)
        for number in possible_numbers:
            if self._is_valid_tckn(number):
                text = text.replace(number, "<TCKN>")
        return text

    def _is_valid_tckn(self, number: str) -> bool:
        """TCKN doğrulama algoritması."""
        if (
            not number.isdigit()
            or len(number) != 11
            or number[0] == "0"
        ):
            return False
        digits = [int(d) for d in number]
        odd_sum = (
            digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
        )
        even_sum = digits[1] + digits[3] + digits[5] + digits[7]
        tenth_digit = ((odd_sum * 7) - even_sum) % 10
        eleventh_digit = sum(digits[:10]) % 10
        return digits[9] == tenth_digit and digits[10] == eleventh_digit

    def _detect_pii_column_type(self, column_name: str) -> str | None:
        """
        Kolon adına göre PII tipini tahmin eder.

        Örnek:
        customer_name -> <PERSON>
        email -> <EMAIL>
        telefon -> <PHONE>
        tc_no -> <TCKN>
        """

        normalized_column = self._normalize_column_name(column_name)

        pii_column_patterns = {
            "<EMAIL>": [
                "email",
                "mail",
                "eposta",
                "epostaadresi",
                "emailaddress",
                "contactemail",
                "billingemail",
                "shippingemail",
            ],
            "<PHONE>": [
                "phone",
                "telefon",
                "tel",
                "gsm",
                "mobile",
                "phonenumber",
                "telefonnumarasi",
                "contactphone",
                "mobilephone",
                "shippingphone",
                "billingphone",
                "msisdn",
            ],
            "<TCKN>": [
                "tckn",
                "tcno",
                "tckimlik",
                "tckimlikno",
                "tckimliknumarasi",
                "kimlikno",
                "identitynumber",
                "nationalid",
                "nationalidentitynumber",
            ],
            "<PERSON>": [
                "name",
                "fullname",
                "firstname",
                "lastname",
                "customername",
                "clientname",
                "username",
                "adsoyad",
                "adsoyadi",
                "isim",
                "soyisim",
                "musteriadi",
                "hastaadi",
                "kullaniciadi",
                "contactname",
                "authorizedperson",
                "yetkilikisi",
            ],
            "<ADDRESS>": [
                "address",
                "adres",
                "customeraddress",
                "billingaddress",
                "shippingaddress",
                "evadresi",
                "isadresi",
            ],
            "<IBAN>": [
                "iban",
                "bankaccount",
                "bankaccountnumber",
                "hesapno",
                "hesapnumarasi",
            ],
            "<BIRTH_DATE>": [
                "birthdate",
                "dateofbirth",
                "dogumtarihi",
                "dogumgunu",
            ],
        }

        for replacement, patterns in pii_column_patterns.items():
            for pattern in patterns:
                if normalized_column == pattern:
                    return replacement

                if len(pattern) >= 5 and pattern in normalized_column:
                    return replacement

        return None

    def _normalize_column_name(self, column_name: str) -> str:
        """
        Kolon adını karşılaştırma için sadeleştirir:
        - Türkçe karakterleri Latin harflere çevirir,
        - Küçük harfe çevirir,
        - Harf ve rakam dışındaki karakterleri siler.
        """
        translation_table = str.maketrans(
            {
                "ç": "c",
                "ğ": "g",
                "ı": "i",
                "i": "i",
                "ö": "o",
                "ş": "s",
                "ü": "u",
                "Ç": "c",
                "Ğ": "g",
                "İ": "i",
                "I": "i",
                "Ö": "o",
                "Ş": "s",
                "Ü": "u",
            }
        )
        normalized = column_name.translate(translation_table)
        normalized = normalized.casefold()
        normalized = re.sub(r"[^a-z0-9]", "", normalized)
        return normalized