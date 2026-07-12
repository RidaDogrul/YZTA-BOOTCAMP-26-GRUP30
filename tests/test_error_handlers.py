from fastapi import status
import pytest

from src.utils.error_handlers import (
    AppError,
    AppValidationError,
    DatabaseConnectionError,
    build_error_response,
    retry_on_exception,
    to_http_exception,
)


def test_app_error_to_dict():
    error = AppError(
        "Test hatası",
        error_code="test_error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        retryable=True,
    )

    assert error.to_dict() == {
        "detail": "Test hatası",
        "error_code": "test_error",
        "retryable": True,
    }


def test_validation_error_metadata():
    error = AppValidationError("Geçersiz istek.")

    assert error.status_code == 400
    assert error.error_code == "validation_error"
    assert error.retryable is False


def test_database_error_is_retryable():
    error = DatabaseConnectionError()

    assert error.status_code == 503
    assert error.error_code == "database_connection_error"
    assert error.retryable is True


def test_build_error_response_for_app_error():
    error = AppValidationError("session_id boş olamaz.")

    response = build_error_response(error)

    assert response["detail"] == "session_id boş olamaz."
    assert response["error_code"] == "validation_error"
    assert response["retryable"] is False


def test_build_error_response_masks_unexpected_error():
    response = build_error_response(RuntimeError("secret internal error"))

    assert response["detail"] == "Beklenmeyen bir hata oluştu."
    assert response["error_code"] == "internal_error"
    assert response["retryable"] is False


def test_to_http_exception_converts_app_error():
    error = AppValidationError("Geçersiz istek.")

    http_error = to_http_exception(error)

    assert http_error.status_code == 400
    assert http_error.detail["error_code"] == "validation_error"


def test_retry_on_exception_succeeds_after_retry():
    calls = {"count": 0}

    @retry_on_exception(
        max_attempts=3,
        delay_seconds=0,
        retry_exceptions=(ValueError,),
    )
    def flaky_operation() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("temporary failure")
        return "ok"

    assert flaky_operation() == "ok"
    assert calls["count"] == 3


def test_retry_on_exception_raises_after_max_attempts():
    calls = {"count": 0}

    @retry_on_exception(
        max_attempts=2,
        delay_seconds=0,
        retry_exceptions=(ValueError,),
    )
    def failing_operation() -> str:
        calls["count"] += 1
        raise ValueError("still failing")

    with pytest.raises(ValueError):
        failing_operation()

    assert calls["count"] == 2


def test_retry_on_exception_rejects_invalid_attempt_count():
    with pytest.raises(ValueError):
        retry_on_exception(max_attempts=0)