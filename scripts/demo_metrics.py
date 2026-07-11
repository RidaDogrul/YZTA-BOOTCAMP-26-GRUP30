from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.metrics import (
    PerformanceMetricsMiddleware,
    log_token_usage,
    measure_model_inference,
)


def build_demo_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(PerformanceMetricsMiddleware)

    @app.get("/demo-health")
    def demo_health():
        return {"status": "ok"}

    return app


def main() -> None:
    print("API LATENCY VE REQUEST-ID DEMOSU")
    client = TestClient(build_demo_app())
    response = client.get(
        "/demo-health",
        headers={"X-Request-ID": "req-demo-metrics-001"},
    )
    print("Response:", response.json())
    print("X-Request-ID:", response.headers["X-Request-ID"])

    print("\nMODEL INFERENCE SÜRESİ DEMOSU")
    with measure_model_inference("demo-model", phase="validation"):
        sum(number * number for number in range(50_000))

    print("\nTOKEN KULLANIMI DEMOSU")
    fake_response = SimpleNamespace(
        usage_metadata={
            "input_tokens": 840,
            "output_tokens": 126,
            "total_tokens": 966,
        },
        response_metadata={"model_name": "gemini-2.5-flash"},
    )
    usage = log_token_usage(fake_response)
    print("Token usage:", usage)


if __name__ == "__main__":
    main()
