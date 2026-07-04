import json
import logging

from src.utils.logger import (
    JSONFormatter,
    clear_request_id,
    get_logger,
    get_request_id,
    mask_sensitive_value,
    set_request_id,
)


def test_set_request_id_generates_id():
    request_id = set_request_id()

    assert request_id is not None
    assert get_request_id() == request_id

    clear_request_id()


def test_set_request_id_uses_given_value():
    request_id = set_request_id("req-test-123")

    assert request_id == "req-test-123"
    assert get_request_id() == "req-test-123"

    clear_request_id()


def test_mask_sensitive_text_values():
    text = "Email: test@example.com Telefon: 05551234567 TCKN: 10000000146"

    result = mask_sensitive_value(text)

    assert "test@example.com" not in result
    assert "05551234567" not in result
    assert "10000000146" not in result

    assert "<EMAIL>" in result
    assert "<PHONE>" in result
    assert "<TCKN>" in result


def test_mask_sensitive_dict_keys():
    data = {
        "customer_name": "John Smith",
        "email": "john@example.com",
        "telefon": "05551234567",
        "password": "super-secret",
        "total_order": 1200,
    }

    result = mask_sensitive_value(data)

    assert result["customer_name"] == "<PERSON>"
    assert result["email"] == "<EMAIL>"
    assert result["telefon"] == "<PHONE>"
    assert result["password"] == "<SECRET>"
    assert result["total_order"] == 1200


def test_mask_nested_data():
    data = {
        "user": {
            "email": "nested@example.com",
            "phone": "05551234567",
        },
        "items": [
            {"customer_name": "John Smith"},
            {"total_order": 1500},
        ],
    }

    result = mask_sensitive_value(data)

    assert result["user"]["email"] == "<EMAIL>"
    assert result["user"]["phone"] == "<PHONE>"
    assert result["items"][0]["customer_name"] == "<PERSON>"
    assert result["items"][1]["total_order"] == 1500


def test_json_formatter_creates_valid_json():
    clear_request_id()
    set_request_id("req-test-123")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="User email is test@example.com",
        args=(),
        exc_info=None,
    )

    record.customer_name = "John Smith"
    record.phone = "05551234567"
    record.total_order = 1200

    formatter = JSONFormatter()
    formatted_log = formatter.format(record)
    log_data = json.loads(formatted_log)

    assert log_data["request_id"] == "req-test-123"
    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test_logger"

    assert "test@example.com" not in formatted_log
    assert "05551234567" not in formatted_log
    assert "John Smith" not in formatted_log

    assert log_data["message"] == "User email is <EMAIL>"
    assert log_data["customer_name"] == "<PERSON>"
    assert log_data["phone"] == "<PHONE>"
    assert log_data["total_order"] == 1200

    clear_request_id()


def test_get_logger_returns_logger_instance():
    logger = get_logger("test_logger_instance")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger_instance"
    assert len(logger.handlers) >= 1