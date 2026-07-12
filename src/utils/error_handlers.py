"""
Common error handling and retry utilities.

Sprint 2 - S2-M3 scope:
- Provide reusable application error classes.
- Convert internal errors into clean API-friendly error payloads.
- Provide a lightweight retry decorator for transient failures.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from fastapi import HTTPException, status

from src.utils.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class AppError(Exception):
    """Base application error with API-friendly metadata."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "app_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "detail": self.message,
            "error_code": self.error_code,
            "retryable": self.retryable,
        }


class AppValidationError(AppError):
    """Raised when user input or request payload is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            error_code="validation_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            retryable=False,
        )


class DatabaseConnectionError(AppError):
    """Raised when a database connection fails."""

    def __init__(self, message: str = "Veritabanı bağlantı hatası.") -> None:
        super().__init__(
            message,
            error_code="database_connection_error",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
        )


class LLMServiceError(AppError):
    """Raised when the LLM service fails or times out."""

    def __init__(self, message: str = "LLM servisi geçici olarak kullanılamıyor.") -> None:
        super().__init__(
            message,
            error_code="llm_service_error",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
        )


class SQLExecutionError(AppError):
    """Raised when SQL generation or execution fails."""

    def __init__(self, message: str = "SQL sorgusu çalıştırılamadı.") -> None:
        super().__init__(
            message,
            error_code="sql_execution_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=False,
        )


class OrchestratorError(AppError):
    """Raised when the agent orchestration pipeline fails."""

    def __init__(self, message: str = "Ajan pipeline hatası oluştu.") -> None:
        super().__init__(
            message,
            error_code="orchestrator_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=False,
        )


def build_error_response(exc: Exception) -> dict[str, Any]:
    """
    Build a safe API error payload.

    AppError details are returned directly.
    Unexpected exceptions are masked to avoid leaking internals.
    """
    if isinstance(exc, AppError):
        return exc.to_dict()

    return {
        "detail": "Beklenmeyen bir hata oluştu.",
        "error_code": "internal_error",
        "retryable": False,
    }


def to_http_exception(exc: AppError) -> HTTPException:
    """Convert an AppError into a FastAPI HTTPException."""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.to_dict(),
    )


def retry_on_exception(
    *,
    max_attempts: int = 3,
    delay_seconds: float = 0.0,
    backoff_multiplier: float = 1.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Retry a function when one of the configured exceptions is raised.

    This is intentionally lightweight for Sprint 2 MVP.
    It can later be replaced with a more advanced retry library if needed.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts en az 1 olmalıdır.")

    if delay_seconds < 0:
        raise ValueError("delay_seconds negatif olamaz.")

    if backoff_multiplier < 1:
        raise ValueError("backoff_multiplier en az 1 olmalıdır.")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_delay = delay_seconds

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "Retry denemeleri tükendi.",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "error": str(exc),
                            },
                        )
                        raise

                    logger.warning(
                        "Geçici hata yakalandı, tekrar denenecek.",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "error": str(exc),
                        },
                    )

                    if current_delay > 0:
                        time.sleep(current_delay)
                        current_delay *= backoff_multiplier

            raise RuntimeError("Retry mekanizması beklenmeyen şekilde tamamlandı.")

        return wrapper

    return decorator