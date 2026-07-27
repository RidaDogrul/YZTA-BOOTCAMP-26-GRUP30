from types import SimpleNamespace
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import src.utils.metrics as metrics_module
from src.utils.logger import get_request_id, mask_sensitive_value
from src.utils.metrics import (
    PerformanceMetricsMiddleware,
    extract_token_usage,
    log_token_usage,
    measure_model_inference,
)


def build_test_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(PerformanceMetricsMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"request_id": get_request_id()}

    return TestClient(app)


def test_middleware_preserves_valid_request_id():
    client = build_test_client()

    response = client.get(
        "/test",
        headers={"X-Request-ID": "req-test-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-123"
    assert response.json()["request_id"] == "req-test-123"


def test_middleware_generates_request_id_when_missing():
    client = build_test_client()

    response = client.get("/test")

    generated_id = response.headers["X-Request-ID"]
    assert response.json()["request_id"] == generated_id
    assert str(uuid.UUID(generated_id)) == generated_id


def test_middleware_replaces_unsafe_request_id():
    client = build_test_client()

    response = client.get(
        "/test",
        headers={"X-Request-ID": "unsafe request id!"},
    )

    generated_id = response.headers["X-Request-ID"]
    assert generated_id != "unsafe request id!"
    assert str(uuid.UUID(generated_id)) == generated_id


def test_middleware_logs_api_latency(monkeypatch):
    captured: list[dict] = []

    def capture_info(message, extra):
        captured.append({"message": message, "extra": extra})

    monkeypatch.setattr(metrics_module.logger, "info", capture_info)
    client = build_test_client()

    response = client.get("/test")

    assert response.status_code == 200
    metric = captured[-1]["extra"]
    assert metric["metric_type"] == "api_latency"
    assert metric["method"] == "GET"
    assert metric["path"] == "/test"
    assert metric["status_code"] == 200
    assert metric["duration_ms"] >= 0
    assert metric["success"] is True


def test_measure_model_inference_logs_success(monkeypatch):
    captured: list[dict] = []
    times = iter([10.0, 10.125])

    monkeypatch.setattr(metrics_module.time, "perf_counter", lambda: next(times))
    monkeypatch.setattr(
        metrics_module.logger,
        "info",
        lambda message, extra: captured.append(extra),
    )

    with measure_model_inference("prophet", phase="validation"):
        result = 2 + 2

    assert result == 4
    assert captured[-1]["metric_type"] == "model_inference"
    assert captured[-1]["model"] == "prophet"
    assert captured[-1]["phase"] == "validation"
    assert captured[-1]["duration_ms"] == pytest.approx(125.0)
    assert captured[-1]["success"] is True


def test_measure_model_inference_logs_failure(monkeypatch):
    captured: list[dict] = []
    times = iter([20.0, 20.25])

    monkeypatch.setattr(metrics_module.time, "perf_counter", lambda: next(times))
    monkeypatch.setattr(
        metrics_module.logger,
        "error",
        lambda message, extra: captured.append(extra),
    )

    with pytest.raises(RuntimeError, match="model hatası"):
        with measure_model_inference("arima", phase="final_forecast"):
            raise RuntimeError("model hatası")

    assert captured[-1]["metric_type"] == "model_inference"
    assert captured[-1]["model"] == "arima"
    assert captured[-1]["duration_ms"] == pytest.approx(250.0)
    assert captured[-1]["success"] is False


def test_extract_token_usage_from_usage_metadata():
    response = SimpleNamespace(
        usage_metadata={
            "input_tokens": 120,
            "output_tokens": 30,
            "total_tokens": 150,
        },
        response_metadata={"model_name": "gemini-2.5-flash"},
    )

    usage = extract_token_usage(response)

    assert usage is not None
    assert usage.input_tokens == 120
    assert usage.output_tokens == 30
    assert usage.total_tokens == 150
    assert usage.model == "gemini-2.5-flash"


def test_extract_token_usage_supports_alternative_keys():
    response = SimpleNamespace(
        usage_metadata=None,
        response_metadata={
            "model": "test-model",
            "token_usage": {
                "prompt_tokens": 40,
                "completion_tokens": 10,
            },
        },
    )

    usage = extract_token_usage(response)

    assert usage is not None
    assert usage.input_tokens == 40
    assert usage.output_tokens == 10
    assert usage.total_tokens == 50
    assert usage.model == "test-model"


def test_log_token_usage_uses_unmasked_numeric_structure(monkeypatch):
    captured: list[dict] = []
    response = SimpleNamespace(
        usage_metadata={
            "input_tokens": 80,
            "output_tokens": 20,
            "total_tokens": 100,
        },
        response_metadata={"model_name": "gemini-test"},
    )

    monkeypatch.setattr(
        metrics_module.logger,
        "info",
        lambda message, extra: captured.append(extra),
    )

    usage = log_token_usage(response)
    masked = mask_sensitive_value(captured[-1])

    assert usage is not None
    assert masked["usage"] == {"input": 80, "output": 20, "total": 100}
    assert masked["metric_type"] == "token_usage"


def test_log_token_usage_returns_none_when_metadata_missing(monkeypatch):
    captured: list[dict] = []
    response = SimpleNamespace(
        usage_metadata=None,
        response_metadata={},
    )

    monkeypatch.setattr(
        metrics_module.logger,
        "warning",
        lambda message, extra: captured.append(extra),
    )

    result = log_token_usage(response)

    assert result is None
    assert captured[-1]["metric_type"] == "token_usage"
    assert captured[-1]["usage_available"] is False
