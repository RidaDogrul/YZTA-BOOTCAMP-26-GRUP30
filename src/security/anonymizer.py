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

    def anonymize_text(
        self,
        text: str,
        *,
        mask_person: bool = True,
    ) -> str:
        """
        Metin içindeki kişisel verileri maskeler.

        mask_person=False olduğunda PERSON tanıması kapatılır. E-posta,
        telefon ve TCKN maskelemesi çalışmaya devam eder. Bu seçenek şehir
        gibi yapılandırılmış konum değerlerinin kişi sanılmasını önlemek
        için kullanılır.
        """
        if not text:
            return text

        entities = ["EMAIL_ADDRESS"]
        operators = {
            "EMAIL_ADDRESS": OperatorConfig(
                "replace",
                {"new_value": "<EMAIL>"},
            ),
        }

        if mask_person:
            entities.append("PERSON")
            operators["PERSON"] = OperatorConfig(
                "replace",
                {"new_value": "<PERSON>"},
            )

        # Presidio analizini çalıştır
        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=entities,
        )
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
        Konum alanlarında ise yanlış PERSON tespitini önlemek için kişi
        tanıması kapatılır.
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
            is_location = (
                key_hint is not None
                and self._is_location_column(key_hint)
            )
            return self.anonymize_text(
                value,
                mask_person=not is_location,
            )

        return value

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Pandas DataFrame içindeki PII verileri maskeler.

        Önce kolon adına bakar:
        - email/mail/e_posta -> <EMAIL>
        - phone/telefon/gsm -> <PHONE>
        - tckn/tc_no/tc_kimlik -> <TCKN>
        - name/ad_soyad/isim/customer_name -> <PERSON>

        Konum kolonlarında PERSON tanıması kapatılır; diğer PII kontrolleri
        çalışmaya devam eder. Diğer metin kolonlarında mevcut genel metin
        analizi uygulanır.
        """
        anonymized_df = df.copy()

        for column in anonymized_df.columns:
            pii_type = self._detect_pii_column_type(column)

            if pii_type:
                anonymized_df[column] = anonymized_df[column].apply(
                    lambda value: value if pd.isna(value) else pii_type
                )
            elif is_string_dtype(anonymized_df[column]):
                is_location = self._is_location_column(column)
                anonymized_df[column] = anonymized_df[column].apply(
                    lambda value: self.anonymize_text(
                        value,
                        mask_person=not is_location,
                    )
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

    def _is_location_column(self, column_name: str) -> bool:
        """
        Genel coğrafi kategori içeren kolonları tanır.

        Bu alanlar açık adres değildir. Grafiklerde kullanılan şehir, ilçe,
        ülke ve bölge gibi toplulaştırılmış konum etiketlerini korumak için
        yalnızca PERSON tanıması kapatılır.
        """
        normalized_column = self._normalize_column_name(column_name)

        location_column_patterns = {
            "city",
            "cityname",
            "customercity",
            "clientcity",
            "billingcity",
            "shippingcity",
            "deliverycity",
            "ordercity",
            "sehir",
            "sehri",
            "sehiradi",
            "musterisehri",
            "faturasehri",
            "teslimatsehri",
            "province",
            "provincename",
            "customerprovince",
            "billingprovince",
            "shippingprovince",
            "il",
            "iladi",
            "musteriili",
            "faturaili",
            "teslimatili",
            "district",
            "districtname",
            "customerdistrict",
            "billingdistrict",
            "shippingdistrict",
            "ilce",
            "ilceadi",
            "musteriilcesi",
            "faturailcesi",
            "teslimatilcesi",
            "country",
            "countryname",
            "customercountry",
            "billingcountry",
            "shippingcountry",
            "ulke",
            "ulkeadi",
            "musteriulkesi",
            "faturaulkesi",
            "teslimatulkesi",
            "state",
            "statename",
            "region",
            "regionname",
            "salesregion",
            "bolge",
            "bolgeadi",
            "satisbolgesi",
        }

        return normalized_column in location_column_patterns

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
