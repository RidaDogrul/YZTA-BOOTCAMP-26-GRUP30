import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from pandas.api.types import is_string_dtype
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

PERSON_ALIAS_PREFIX = "Customer"


@dataclass
class _PseudonymizationContext:
    """
    Tek bir anonimleştirme işlemi boyunca kişi etiketlerini tutar.

    Ham isimler kalıcı olarak saklanmaz. Context, anonymize_text,
    anonymize_dict veya anonymize_dataframe çağrısı tamamlandığında
    erişilemez hâle gelir.
    """

    aliases: dict[tuple[str, str], str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)

    def alias_for(self, value: Any, role: str) -> str:
        """Aynı kişi değeri için aynı Customer takma etiketini döndürür."""
        # Rol parametresi mevcut çağrı noktalarıyla uyumluluk için korunur.
        # Kullanıcıya gösterilen bütün kişi etiketleri tek prefix kullanır.
        role = PERSON_ALIAS_PREFIX
        normalized_value = unicodedata.normalize(
            "NFKC",
            str(value),
        )
        normalized_value = normalized_value.replace("İ", "i").replace(
            "I",
            "ı",
        )
        normalized_value = " ".join(normalized_value.split()).casefold()
        alias_key = (role, normalized_value)

        if alias_key not in self.aliases:
            next_number = self.counters.get(role, 0) + 1
            self.counters[role] = next_number
            self.aliases[alias_key] = f"{role}-{next_number:03d}"

        return self.aliases[alias_key]


class PIIAnonymizer:
    """
    Kişisel verileri maskeler ve kişi adlarını takma kimliklerle değiştirir.

    Örnek:
        John Smith'in maili john@example.com

    çıktısı:
        Customer-001'in maili <EMAIL>

    Yapılandırılmış veya serbest metindeki bütün kişi değerleri tek bir
    standartla etiketlenir:
        customer_name -> Customer-001
        employee_name -> Customer-002

    Takma kimlik eşlemesi yalnızca tek bir public metot çağrısı boyunca
    geçerlidir. Bu sayede aynı raporda aynı kişi ayırt edilebilir; farklı
    raporlar arasında kalıcı olarak izlenemez.
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

        Serbest metindeki kişiler Customer-001, Customer-002 biçiminde
        etiketlenir.
        """
        if not text:
            return text

        context = _PseudonymizationContext()
        return self._anonymize_text_with_context(
            text,
            mask_person=mask_person,
            context=context,
            person_role="Kişi",
        )

    def _anonymize_text_with_context(
        self,
        text: str,
        *,
        mask_person: bool,
        context: _PseudonymizationContext,
        person_role: str,
    ) -> str:
        """
        Ortak context kullanarak metni anonimleştirir.

        DataFrame ve iç içe sözlüklerde bu yardımcı metot kullanıldığı için
        aynı kişi aynı anonimleştirme işlemi boyunca aynı etiketi alır.
        """
        entities = ["EMAIL_ADDRESS"]
        if mask_person:
            entities.append("PERSON")

        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=entities,
        )

        anonymized_text = text
        selected_results = self._select_non_overlapping_results(results)

        for result in sorted(
            selected_results,
            key=lambda item: (item.start, item.end),
            reverse=True,
        ):
            original_value = text[result.start : result.end]

            if result.entity_type == "PERSON":
                replacement = context.alias_for(
                    original_value,
                    person_role,
                )
            elif result.entity_type == "EMAIL_ADDRESS":
                replacement = "<EMAIL>"
            else:
                continue

            anonymized_text = (
                anonymized_text[: result.start]
                + replacement
                + anonymized_text[result.end :]
            )

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
        context = _PseudonymizationContext()
        return {
            key: self._anonymize_value(
                value,
                key_hint=str(key),
                context=context,
            )
            for key, value in data.items()
        }

    def _anonymize_value(
        self,
        value: Any,
        key_hint: str | None = None,
        *,
        context: _PseudonymizationContext,
        inherited_role: str | None = None,
    ) -> Any:
        """
        İç içe dict, list ve tuple yapılarını recursive olarak işler.

        key_hint verilmişse email, telefon, TCKN ve kişi adı gibi alanlar
        yalnızca metin analizine bağlı kalmadan kesin olarak maskelenir.
        Konum alanlarında ise yanlış PERSON tespitini önlemek için kişi
        tanıması kapatılır.
        """
        current_role = self._detect_role_hint(key_hint) or inherited_role

        if isinstance(value, dict):
            return {
                key: self._anonymize_value(
                    item,
                    key_hint=str(key),
                    context=context,
                    inherited_role=current_role,
                )
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                self._anonymize_value(
                    item,
                    key_hint=key_hint,
                    context=context,
                    inherited_role=current_role,
                )
                for item in value
            ]

        if isinstance(value, tuple):
            return tuple(
                self._anonymize_value(
                    item,
                    key_hint=key_hint,
                    context=context,
                    inherited_role=current_role,
                )
                for item in value
            )

        if key_hint is not None:
            pii_type = self._detect_pii_column_type(key_hint)

            if pii_type is not None:
                if self._is_missing_value(value):
                    return value

                if pii_type == "<PERSON>":
                    specific_role = self._detect_person_role(key_hint)
                    person_role = (
                        specific_role or inherited_role or current_role or "Kişi"
                    )
                    return self._pseudonymize_structured_person(
                        value,
                        role=person_role,
                        context=context,
                    )

                return pii_type

        if isinstance(value, str):
            is_location = key_hint is not None and self._is_location_column(key_hint)
            return self._anonymize_text_with_context(
                value,
                mask_person=not is_location,
                context=context,
                person_role=current_role or "Kişi",
            )

        return value

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Pandas DataFrame içindeki PII verileri maskeler.

        Önce kolon adına bakar:
        - email/mail/e_posta -> <EMAIL>
        - phone/telefon/gsm -> <PHONE>
        - tckn/tc_no/tc_kimlik -> <TCKN>
        - customer_name -> Customer-001, Customer-002
        - employee_name -> Customer-001, Customer-002
        - name/ad_soyad/isim -> Customer-001, Customer-002

        Konum kolonlarında PERSON tanıması kapatılır; diğer PII kontrolleri
        çalışmaya devam eder. Diğer metin kolonlarında mevcut genel metin
        analizi uygulanır.
        """
        anonymized_df = df.copy()
        context = _PseudonymizationContext()

        for column in anonymized_df.columns:
            pii_type = self._detect_pii_column_type(column)

            if pii_type == "<PERSON>":
                person_role = (
                    self._detect_person_role(column)
                    or self._detect_role_hint(column)
                    or "Kişi"
                )
                anonymized_df[column] = anonymized_df[column].apply(
                    lambda value, role=person_role: (
                        self._pseudonymize_structured_person(
                            value,
                            role=role,
                            context=context,
                        )
                    )
                )
            elif pii_type:
                anonymized_df[column] = anonymized_df[column].apply(
                    lambda value, replacement=pii_type: (
                        value if self._is_missing_value(value) else replacement
                    )
                )
            elif is_string_dtype(anonymized_df[column]):
                is_location = self._is_location_column(column)
                person_role = self._detect_role_hint(column) or "Kişi"
                anonymized_df[column] = anonymized_df[column].apply(
                    lambda value, location=is_location, role=person_role: (
                        self._anonymize_text_with_context(
                            value,
                            mask_person=not location,
                            context=context,
                            person_role=role,
                        )
                        if isinstance(value, str)
                        else value
                    )
                )

        return anonymized_df

    # Dahili yardımcı fonksiyonlar

    def _select_non_overlapping_results(
        self,
        results: list[Any],
    ) -> list[Any]:
        """
        Çakışan Presidio sonuçlarından güvenli olanları seçer.

        E-posta gibi biçimi açık bir varlık, aynı aralığı PERSON olarak
        işaretleyen tahminden önceliklidir. Kalan sonuçlarda skor ve daha
        uzun metin aralığı tercih edilir.
        """
        entity_priority = {
            "EMAIL_ADDRESS": 2,
            "PERSON": 1,
        }
        ordered_results = sorted(
            results,
            key=lambda item: (
                entity_priority.get(item.entity_type, 0),
                getattr(item, "score", 0.0),
                item.end - item.start,
            ),
            reverse=True,
        )
        selected: list[Any] = []

        for candidate in ordered_results:
            if candidate.start < 0 or candidate.end <= candidate.start:
                continue

            overlaps_existing = any(
                candidate.start < existing.end and existing.start < candidate.end
                for existing in selected
            )
            if not overlaps_existing:
                selected.append(candidate)

        return selected

    def _pseudonymize_structured_person(
        self,
        value: Any,
        *,
        role: str,
        context: _PseudonymizationContext,
    ) -> Any:
        """Yapılandırılmış kişi değerini rol bazlı takma kimliğe çevirir."""
        if self._is_missing_value(value):
            return value

        if isinstance(value, str) and not value.strip():
            return value

        if isinstance(value, str) and self._is_person_alias(value):
            return value

        return context.alias_for(value, role)

    def _is_person_alias(self, value: str) -> bool:
        """Daha önce üretilmiş rol bazlı kişi etiketlerini tanır."""
        person_alias_pattern = (
            r"^(?:Customer|Müşteri|Çalışan|Hasta|Tedarikçi|Yetkili|"
            r"Kullanıcı|Kişi)-\d{3,}$"
        )
        return re.fullmatch(person_alias_pattern, value.strip()) is not None

    def _is_missing_value(self, value: Any) -> bool:
        """None, NaN, NaT ve pd.NA gibi eksik skaler değerleri tanır."""
        if value is None:
            return True

        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False

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
        if not number.isdigit() or len(number) != 11 or number[0] == "0":
            return False
        digits = [int(d) for d in number]
        odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
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
                "employeename",
                "staffname",
                "personnelname",
                "patientname",
                "username",
                "adsoyad",
                "adsoyadi",
                "isim",
                "soyisim",
                "musteriadi",
                "calisanadi",
                "personeladi",
                "hastaadi",
                "kullaniciadi",
                "contactname",
                "authorizedperson",
                "yetkilikisi",
                "suppliercontactname",
                "vendorcontactname",
                "tedarikciyetkilisi",
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

    def _detect_person_role(self, column_name: str) -> str | None:
        """
        Yapılandırılmış kişi alanının iş rolünü döndürür.

        Genel name/ad_soyad gibi alanlarda rol tahmin edilmez; üst
        container'dan gelen rol veya Kişi varsayılanı kullanılır.
        """
        return self._detect_role_hint(column_name)

    def _detect_role_hint(
        self,
        field_name: str | None,
    ) -> str | None:
        """
        Alan veya container adına göre kişi rolünü belirler.

        Örneğin customers listesinin içindeki genel name alanı, üst
        container'dan Müşteri rolünü devralır.
        """
        if field_name is None:
            return None

        normalized_field = self._normalize_column_name(field_name)
        role_patterns = [
            (
                "Müşteri",
                {
                    "customer",
                    "customers",
                    "customername",
                    "client",
                    "clients",
                    "clientname",
                    "musteri",
                    "musteriler",
                    "musteriadi",
                },
            ),
            (
                "Çalışan",
                {
                    "employee",
                    "employees",
                    "employeename",
                    "staff",
                    "staffname",
                    "personnel",
                    "personnelname",
                    "calisan",
                    "calisanlar",
                    "calisanadi",
                    "personel",
                    "personeller",
                    "personeladi",
                },
            ),
            (
                "Hasta",
                {
                    "patient",
                    "patients",
                    "patientname",
                    "hasta",
                    "hastalar",
                    "hastaadi",
                },
            ),
            (
                "Tedarikçi",
                {
                    "supplier",
                    "suppliers",
                    "suppliercontactname",
                    "vendor",
                    "vendors",
                    "vendorcontactname",
                    "tedarikci",
                    "tedarikciler",
                    "tedarikciyetkilisi",
                },
            ),
            (
                "Yetkili",
                {
                    "contact",
                    "contacts",
                    "contactname",
                    "authorizedperson",
                    "yetkili",
                    "yetkililer",
                    "yetkilikisi",
                },
            ),
            (
                "Kullanıcı",
                {
                    "user",
                    "users",
                    "username",
                    "kullanici",
                    "kullanicilar",
                    "kullaniciadi",
                },
            ),
        ]

        for role, patterns in role_patterns:
            for pattern in patterns:
                if normalized_field == pattern:
                    return role

                if len(pattern) >= 5 and pattern in normalized_field:
                    return role

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
