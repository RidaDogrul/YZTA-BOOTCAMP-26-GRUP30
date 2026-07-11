from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import re
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.utils.logger import clear_request_id, get_logger, set_request_id


logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 128
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


@dataclass(frozen=True)
class TokenUsage:
    """Bir LLM yanıtından çıkarılan token kullanım bilgileri."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str | None = None

    def as_log_extra(self) -> dict[str, Any]:
        """Logger'ın token değerlerini sır olarak maskelemeyeceği güvenli yapı."""
        return {
            "metric_type": "token_usage",
            "model": self.model,
            "usage": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "total": self.total_tokens,
            },
        }


def _sanitize_request_id(value: str | None) -> str | None:
    """Güvenli biçimde kullanılabilecek istemci request-id değerini döndürür."""
    if value is None:
        return None

    candidate = value.strip()
    if not candidate or len(candidate) > MAX_REQUEST_ID_LENGTH:
        return None

    if _REQUEST_ID_PATTERN.fullmatch(candidate) is None:
        return None

    return candidate


class PerformanceMetricsMiddleware(BaseHTTPMiddleware):
    """Her HTTP isteği için request-id ve API latency metriği üretir."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming_request_id = _sanitize_request_id(
            request.headers.get(REQUEST_ID_HEADER)
        )
        request_id = set_request_id(incoming_request_id)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - started_at) * 1000
            response.headers[REQUEST_ID_HEADER] = request_id
            success = response.status_code < 500

            log_method = logger.info if success else logger.error
            log_method(
                "API isteği tamamlandı",
                extra={
                    "metric_type": "api_latency",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 3),
                    "success": success,
                },
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.error(
                "API isteği hata verdi",
                extra={
                    "metric_type": "api_latency",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 3),
                    "success": False,
                    "error": str(exc),
                },
            )
            raise
        finally:
            clear_request_id()


@contextmanager
def measure_model_inference(
    model_name: str,
    phase: str = "predict",
) -> Iterator[None]:
    """Bir model bloğunun çalışma süresini ölçüp yapılandırılmış log üretir."""
    started_at = time.perf_counter()

    try:
        yield
    except Exception as exc:
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.error(
            "Model inference hata verdi",
            extra={
                "metric_type": "model_inference",
                "model": model_name,
                "phase": phase,
                "duration_ms": round(duration_ms, 3),
                "success": False,
                "error": str(exc),
            },
        )
        raise
    else:
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Model inference tamamlandı",
            extra={
                "metric_type": "model_inference",
                "model": model_name,
                "phase": phase,
                "duration_ms": round(duration_ms, 3),
                "success": True,
            },
        )


def _lookup_usage_value(
    usage: Mapping[str, Any] | Any,
    names: tuple[str, ...],
) -> int | None:
    """Mapping veya nesne içinden ilk bulunan token sayısını okur."""
    for name in names:
        if isinstance(usage, Mapping):
            value = usage.get(name)
        else:
            value = getattr(usage, name, None)

        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue

    return None


def _extract_model_name(response: Any) -> str | None:
    """LLM yanıtının metadata alanından model adını çıkarmaya çalışır."""
    metadata = getattr(response, "response_metadata", None)
    if not isinstance(metadata, Mapping):
        return None

    value = metadata.get("model_name") or metadata.get("model")
    return str(value) if value else None


def extract_token_usage(
    response: Any,
    model_name: str | None = None,
) -> TokenUsage | None:
    """LangChain/LLM yanıtındaki farklı token metadata biçimlerini destekler."""
    usage = getattr(response, "usage_metadata", None)
    response_metadata = getattr(response, "response_metadata", None)

    if usage is None and isinstance(response_metadata, Mapping):
        usage = (
            response_metadata.get("token_usage")
            or response_metadata.get("usage_metadata")
            or response_metadata.get("usage")
        )

    if usage is None:
        return None

    input_tokens = _lookup_usage_value(
        usage,
        ("input_tokens", "prompt_tokens", "prompt_token_count"),
    )
    output_tokens = _lookup_usage_value(
        usage,
        ("output_tokens", "completion_tokens", "candidates_token_count"),
    )
    total_tokens = _lookup_usage_value(
        usage,
        ("total_tokens", "total_token_count"),
    )

    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    input_tokens = input_tokens or 0
    output_tokens = output_tokens or 0
    total_tokens = total_tokens if total_tokens is not None else input_tokens + output_tokens

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        model=model_name or _extract_model_name(response),
    )


def log_token_usage(
    response: Any,
    model_name: str | None = None,
) -> TokenUsage | None:
    """LLM token kullanımını loglar; metadata yoksa uygulamayı durdurmaz."""
    usage = extract_token_usage(response=response, model_name=model_name)

    if usage is None:
        logger.warning(
            "LLM token kullanım bilgisi bulunamadı",
            extra={
                "metric_type": "token_usage",
                "model": model_name or _extract_model_name(response),
                "usage_available": False,
            },
        )
        return None

    logger.info(
        "LLM token kullanımı kaydedildi",
        extra=usage.as_log_extra(),
    )
    return usage
