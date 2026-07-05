import contextvars
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


request_id_var = contextvars.ContextVar("request_id", default=None)


RESERVED_LOG_RECORD_KEYS = {
    "name",
    "taskName",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


SENSITIVE_KEYWORDS = [
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "email",
    "mail",
    "phone",
    "telefon",
    "gsm",
    "mobile",
    "tckn",
    "tc_no",
    "tcno",
    "kimlik",
    "name",
    "full_name",
    "customer_name",
    "ad_soyad",
    "isim",
    "soyisim",
]


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Her istek için takip edilebilir bir request_id oluşturur.
    Eğer request_id verilirse onu kullanır.
    """

    if request_id is None:
        request_id = str(uuid.uuid4())

    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """
    Aktif request_id değerini döndürür.
    """

    return request_id_var.get()


def clear_request_id() -> None:
    """
    Aktif request_id değerini temizler.
    """

    request_id_var.set(None)


def mask_sensitive_value(value: Any) -> Any:
    """
    Log'a yazılmadan önce hassas verileri maskeler.
    """

    if isinstance(value, dict):
        masked_dict = {}

        for key, item in value.items():
            normalized_key = _normalize_key(str(key))

            if _is_sensitive_key(normalized_key):
                masked_dict[key] = _placeholder_for_key(normalized_key)
            else:
                masked_dict[key] = mask_sensitive_value(item)

        return masked_dict

    if isinstance(value, list):
        return [mask_sensitive_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(mask_sensitive_value(item) for item in value)

    if isinstance(value, str):
        return _mask_sensitive_text(value)

    return value


def _mask_sensitive_text(text: str) -> str:
    """
    Serbest metin içindeki formatlı hassas verileri maskeler.
    """

    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

    phone_pattern = (
        r"(?<!\d)"
        r"(?:\+90|0090|0)?"
        r"\s?"
        r"5\d{2}"
        r"\s?"
        r"\d{3}"
        r"\s?"
        r"\d{2}"
        r"\s?"
        r"\d{2}"
        r"(?!\d)"
    )

    possible_tckn_pattern = r"\b[1-9][0-9]{10}\b"

    text = re.sub(email_pattern, "<EMAIL>", text)
    text = re.sub(phone_pattern, "<PHONE>", text)
    text = re.sub(possible_tckn_pattern, "<TCKN>", text)

    return text


def _normalize_key(key: str) -> str:
    """
    Key adını karşılaştırma için sadeleştirir.
    """

    translation_table = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
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

    normalized = key.translate(translation_table)
    normalized = normalized.casefold()
    normalized = re.sub(r"[^a-z0-9]", "", normalized)

    return normalized


def _is_sensitive_key(key: str) -> bool:
    """
    Key adı hassas veri içeriyor mu kontrol eder.
    """

    for keyword in SENSITIVE_KEYWORDS:
        normalized_keyword = _normalize_key(keyword)

        if key == normalized_keyword:
            return True

        if len(normalized_keyword) >= 5 and normalized_keyword in key:
            return True

    return False


def _placeholder_for_key(key: str) -> str:
    """
    Hassas key tipine göre uygun placeholder döndürür.
    """

    if "email" in key or "mail" in key or "eposta" in key:
        return "<EMAIL>"

    if "phone" in key or "telefon" in key or "gsm" in key or "mobile" in key:
        return "<PHONE>"

    if "tckn" in key or "tcno" in key or "kimlik" in key:
        return "<TCKN>"

    if (
        "password" in key
        or "passwd" in key
        or "secret" in key
        or "token" in key
        or "apikey" in key
    ):
        return "<SECRET>"

    if "name" in key or "isim" in key or "soyisim" in key:
        return "<PERSON>"

    return "<MASKED>"


class JSONFormatter(logging.Formatter):
    """
    Log kayıtlarını JSON formatına çevirir.
    Hassas verileri log çıktısına yazmadan önce maskeler.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_value(record.getMessage()),
            "request_id": get_request_id(),
        }

        for key, value in record.__dict__.items():
            if key not in RESERVED_LOG_RECORD_KEYS and not key.startswith("_"):
               normalized_key = _normalize_key(str(key))

               if _is_sensitive_key(normalized_key):
                  log_data[key] = _placeholder_for_key(normalized_key)
               else:
                  log_data[key] = mask_sensitive_value(value)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    JSON formatlı logger döndürür.
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger