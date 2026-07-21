import json

import pandas as pd
import pytest

import src.utils.usage_tracker as usage_module
from src.utils.logger import JSONFormatter, clear_request_id, set_request_id
from src.utils.usage_tracker import (
    UsageTracker,
    estimate_data_size_bytes,
    infer_row_count,
)


def test_estimate_dataframe_size_uses_deep_memory() -> None:
    data = pd.DataFrame(
        {
            "product": ["Klavye", "Monitör"],
            "revenue": [1200.0, 8500.0],
        }
    )

    expected = int(data.memory_usage(index=True, deep=True).sum())

    assert estimate_data_size_bytes(data) == expected
    assert infer_row_count(data) == 2


def test_estimate_utf8_payload_size_without_logging_content() -> None:
    payload = {"city": "İstanbul", "count": 3}
    expected_json = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    assert estimate_data_size_bytes(payload) == len(expected_json.encode("utf-8"))
    assert infer_row_count(payload) == 1


def test_record_query_logs_only_usage_metadata(monkeypatch) -> None:
    captured: list[dict] = []
    tracker = UsageTracker()
    sensitive_data = pd.DataFrame(
        {
            "customer_name": ["Ayşe Yılmaz"],
            "email": ["ayse@example.com"],
        }
    )

    monkeypatch.setattr(
        usage_module.logger,
        "info",
        lambda message, extra: captured.append({"message": message, "extra": extra}),
    )

    record = tracker.record_query(
        result_data=sensitive_data,
        source_type="postgresql",
        tenant_id="tenant-30",
        user_id="user-5",
        session_id="sess-test-1",
    )

    logged = captured[-1]
    serialized_log = json.dumps(logged, ensure_ascii=False)

    assert record.query_count == 1
    assert record.row_count == 1
    assert record.data_size_bytes > 0
    assert record.success is True
    assert record.billable is True
    assert logged["extra"]["metric_type"] == "usage"
    assert logged["extra"]["usage_type"] == "query"
    assert "Ayşe Yılmaz" not in serialized_log
    assert "ayse@example.com" not in serialized_log


def test_failed_query_is_not_billable_by_default(monkeypatch) -> None:
    captured: list[dict] = []
    tracker = UsageTracker()

    monkeypatch.setattr(
        usage_module.logger,
        "warning",
        lambda message, extra: captured.append(extra),
    )

    record = tracker.record_query(
        source_type="mysql",
        success=False,
        row_count=0,
        data_size_bytes=0,
    )

    assert record.query_count == 1
    assert record.billable is False
    assert captured[-1]["success"] is False
    assert captured[-1]["billable"] is False


def test_failed_query_cannot_be_marked_billable() -> None:
    tracker = UsageTracker()

    with pytest.raises(ValueError, match="billable=True"):
        tracker.record_query(
            source_type="mongodb",
            success=False,
            billable=True,
        )


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("row_count", {"row_count": -1}),
        ("data_size_bytes", {"data_size_bytes": -1}),
    ],
)
def test_record_query_rejects_negative_usage_values(field_name, kwargs) -> None:
    tracker = UsageTracker()

    with pytest.raises(ValueError, match=field_name):
        tracker.record_query(source_type="postgresql", **kwargs)


def test_usage_summary_supports_tenant_filtering(monkeypatch) -> None:
    tracker = UsageTracker()
    monkeypatch.setattr(usage_module.logger, "info", lambda message, extra: None)

    tracker.record_query(
        source_type="postgresql",
        tenant_id="tenant-a",
        row_count=10,
        data_size_bytes=1000,
    )
    tracker.record_query(
        source_type="mysql",
        tenant_id="tenant-a",
        row_count=5,
        data_size_bytes=500,
    )
    tracker.record_query(
        source_type="mongodb",
        tenant_id="tenant-b",
        row_count=7,
        data_size_bytes=700,
    )

    summary = tracker.summarize(tenant_id="tenant-a")

    assert summary.total_events == 2
    assert summary.total_query_count == 2
    assert summary.successful_query_count == 2
    assert summary.failed_query_count == 0
    assert summary.billable_query_count == 2
    assert summary.total_row_count == 15
    assert summary.total_data_size_bytes == 1500
    assert summary.billable_data_size_bytes == 1500


def test_usage_summary_separates_failed_and_billable_queries(monkeypatch) -> None:
    tracker = UsageTracker()
    monkeypatch.setattr(usage_module.logger, "info", lambda message, extra: None)
    monkeypatch.setattr(usage_module.logger, "warning", lambda message, extra: None)

    tracker.record_query(
        source_type="postgresql",
        success=True,
        row_count=3,
        data_size_bytes=300,
    )
    tracker.record_query(
        source_type="postgresql",
        success=False,
        row_count=0,
        data_size_bytes=0,
    )

    summary = tracker.summarize()

    assert summary.total_query_count == 2
    assert summary.successful_query_count == 1
    assert summary.failed_query_count == 1
    assert summary.billable_query_count == 1
    assert summary.billable_data_size_bytes == 300


def test_json_logger_adds_request_id_to_usage_event(capsys) -> None:
    clear_request_id()
    set_request_id("req-usage-test-1")
    tracker = UsageTracker()

    try:
        record = tracker.record_query(
            source_type="postgresql",
            session_id="sess-test-1",
            row_count=2,
            data_size_bytes=256,
        )

        formatter = JSONFormatter()
        log_record = usage_module.logger.makeRecord(
            usage_module.logger.name,
            20,
            __file__,
            1,
            "Sorgu kullanımı kaydedildi",
            (),
            None,
            extra=record.as_log_extra(),
        )
        formatted = json.loads(formatter.format(log_record))

        assert formatted["request_id"] == "req-usage-test-1"
        assert formatted["metric_type"] == "usage"
        assert formatted["data_size_bytes"] == 256
    finally:
        clear_request_id()
        capsys.readouterr()


def test_reset_clears_in_memory_usage(monkeypatch) -> None:
    tracker = UsageTracker()
    monkeypatch.setattr(usage_module.logger, "info", lambda message, extra: None)
    tracker.record_query(source_type="postgresql", row_count=1, data_size_bytes=10)

    tracker.reset()

    assert tracker.get_records() == ()
    assert tracker.summarize().total_query_count == 0
