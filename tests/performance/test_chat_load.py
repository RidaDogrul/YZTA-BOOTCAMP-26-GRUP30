from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import Any

import pytest
from fastapi.testclient import TestClient

from main import app
from src.api.v1.schemas.chat import ChatResponse
from src.utils.cache import make_cache_key, query_cache

REQUEST_COUNT = 40
MAX_WORKERS = 8
MAX_AVG_RESPONSE_SECONDS = 1.0


@pytest.fixture(autouse=True)
def clear_load_test_cache():
    query_cache.clear()
    yield
    query_cache.clear()


def _post_chat(payload: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    client = TestClient(app)

    started = perf_counter()
    response = client.post("/api/v1/chat/ask", json=payload)
    elapsed = perf_counter() - started

    return response.status_code, response.json(), elapsed


def test_chat_endpoint_handles_cached_concurrent_load():
    payload = {
        "session_id": "sess_load_cached",
        "question": "Load test cache sorusu",
    }

    cached_response = ChatResponse(
        status="success",
        summary="Cached load test response",
        sql_query="SELECT 1",
        chart_data=[
            {"date": "2026-07-01", "revenue": 12000},
            {"date": "2026-07-02", "revenue": 13200},
        ],
        action_plan=["Keep monitoring cache latency."],
        sources_queried=[
            {
                "source_id": "src_load",
                "alias": "Load Test Source",
                "source_type": "postgresql",
                "success": True,
                "row_count": 2,
                "error": None,
            }
        ],
    )

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
        "[]",
    )
    query_cache.set(cache_key, cached_response)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(_post_chat, payload)
            for _ in range(REQUEST_COUNT)
        ]

        results = [future.result() for future in as_completed(futures)]

    statuses = [status for status, _, _ in results]
    bodies = [body for _, body, _ in results]
    timings = [elapsed for _, _, elapsed in results]

    assert statuses == [200] * REQUEST_COUNT
    assert all(body["status"] == "success" for body in bodies)
    assert all(body["summary"] == "Cached load test response" for body in bodies)
    assert all(body["chart_data"][0]["revenue"] == 12000 for body in bodies)

    avg_response_time = sum(timings) / len(timings)
    assert avg_response_time < MAX_AVG_RESPONSE_SECONDS


def test_chat_endpoint_handles_repeated_invalid_session_load():
    payload = {
        "session_id": "sess_unknown_load",
        "question": "Invalid session load test sorusu",
    }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(_post_chat, payload)
            for _ in range(REQUEST_COUNT)
        ]

        results = [future.result() for future in as_completed(futures)]

    statuses = [status for status, _, _ in results]
    bodies = [body for _, body, _ in results]

    assert statuses == [404] * REQUEST_COUNT
    assert all(
        body["detail"] == "Oturum bulunamadı veya süresi doldu."
        for body in bodies
    )

    cache_key = make_cache_key(
        "chat",
        payload["session_id"],
        payload["question"],
        "[]",
    )
    assert query_cache.get(cache_key) is None
