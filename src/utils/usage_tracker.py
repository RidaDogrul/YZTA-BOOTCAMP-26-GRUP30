from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sys
import threading
from typing import Any
import uuid

import pandas as pd

from src.utils.logger import get_logger


logger = get_logger(__name__)

MAX_DIMENSION_LENGTH = 128


def _normalize_dimension(value: str | None, field_name: str) -> str | None:
    """Log boyutlarında kullanılacak opsiyonel kimliği güvenli hâle getirir."""
    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    if len(normalized) > MAX_DIMENSION_LENGTH:
        raise ValueError(
            f"{field_name} en fazla {MAX_DIMENSION_LENGTH} karakter olabilir."
        )

    if any(character.isspace() or ord(character) < 32 for character in normalized):
        raise ValueError(f"{field_name} boşluk veya kontrol karakteri içeremez.")

    return normalized


def _validate_non_negative(value: int, field_name: str) -> int:
    """Sayaç alanını bool kabul etmeden negatif olmayan int olarak doğrular."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} bir tam sayı olmalıdır.")
    if value < 0:
        raise ValueError(f"{field_name} negatif olamaz.")
    return value


def estimate_data_size_bytes(data: Any) -> int:
    """
    Sonuç verisinin yaklaşık bellek/UTF-8 büyüklüğünü byte cinsinden hesaplar.

    Veri içeriği hiçbir zaman loglanmaz. DataFrame ve Series için pandas'ın
    deep memory hesabı; JSON uyumlu nesneler için UTF-8 serileştirme boyutu
    kullanılır.
    """
    if data is None:
        return 0

    if isinstance(data, pd.DataFrame):
        return int(data.memory_usage(index=True, deep=True).sum())

    if isinstance(data, pd.Series):
        return int(data.memory_usage(index=True, deep=True))

    if isinstance(data, bytes):
        return len(data)

    if isinstance(data, (bytearray, memoryview)):
        return len(bytes(data))

    if isinstance(data, str):
        return len(data.encode("utf-8"))

    try:
        serialized = json.dumps(
            data,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, OverflowError):
        return int(sys.getsizeof(data))

    return len(serialized.encode("utf-8"))


def infer_row_count(data: Any) -> int:
    """Yaygın sorgu sonucu tiplerinden satır sayısını çıkarır."""
    if data is None:
        return 0

    if isinstance(data, (str, bytes, bytearray, memoryview)):
        return 1

    if isinstance(data, dict):
        return 1

    try:
        return len(data)
    except TypeError:
        return 1


@dataclass(frozen=True)
class UsageRecord:
    """Tek bir veri sorgusunun SaaS kullanım olayı."""

    event_id: str
    occurred_at: datetime
    source_type: str
    query_count: int
    row_count: int
    data_size_bytes: int
    success: bool
    billable: bool
    tenant_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    operation: str = "data_query"

    def as_log_extra(self) -> dict[str, Any]:
        """Ham sorgu/veri içermeyen yapılandırılmış kullanım metriği."""
        return {
            "metric_type": "usage",
            "usage_type": "query",
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "source_type": self.source_type,
            "operation": self.operation,
            "query_count": self.query_count,
            "row_count": self.row_count,
            "data_size_bytes": self.data_size_bytes,
            "success": self.success,
            "billable": self.billable,
        }


@dataclass(frozen=True)
class UsageSummary:
    """Bellekte tutulan kullanım kayıtlarının toplu özeti."""

    total_events: int
    total_query_count: int
    successful_query_count: int
    failed_query_count: int
    billable_query_count: int
    total_row_count: int
    total_data_size_bytes: int
    billable_data_size_bytes: int

    def as_dict(self) -> dict[str, int | float]:
        return {
            "total_events": self.total_events,
            "total_query_count": self.total_query_count,
            "successful_query_count": self.successful_query_count,
            "failed_query_count": self.failed_query_count,
            "billable_query_count": self.billable_query_count,
            "total_row_count": self.total_row_count,
            "total_data_size_bytes": self.total_data_size_bytes,
            "billable_data_size_bytes": self.billable_data_size_bytes,
            "total_data_size_mb": round(self.total_data_size_bytes / (1024**2), 6),
        }


class UsageTracker:
    """
    Thread-safe MVP kullanım takipçisi.

    Her olay mevcut JSON logger üzerinden yazılır. Bellekteki kayıtlar demo ve
    anlık özet içindir; production faturalandırmasında log sink/veritabanı kalıcı
    kaynak olarak kullanılmalıdır.
    """

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []
        self._lock = threading.Lock()

    def record_query(
        self,
        *,
        result_data: Any = None,
        source_type: str,
        success: bool = True,
        billable: bool | None = None,
        row_count: int | None = None,
        data_size_bytes: int | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        operation: str = "data_query",
    ) -> UsageRecord:
        """Bir sorguyu sayar, veri büyüklüğünü ölçer ve güvenli JSON log üretir."""
        normalized_source = _normalize_dimension(source_type, "source_type")
        normalized_operation = _normalize_dimension(operation, "operation")

        if normalized_source is None:
            raise ValueError("source_type boş olamaz.")
        if normalized_operation is None:
            raise ValueError("operation boş olamaz.")

        actual_row_count = (
            infer_row_count(result_data)
            if row_count is None
            else _validate_non_negative(row_count, "row_count")
        )
        actual_data_size = (
            estimate_data_size_bytes(result_data)
            if data_size_bytes is None
            else _validate_non_negative(data_size_bytes, "data_size_bytes")
        )

        effective_billable = success if billable is None else billable
        if effective_billable and not success:
            raise ValueError("Başarısız sorgu billable=True olarak kaydedilemez.")

        record = UsageRecord(
            event_id=str(uuid.uuid4()),
            occurred_at=datetime.now(timezone.utc),
            source_type=normalized_source,
            operation=normalized_operation,
            query_count=1,
            row_count=actual_row_count,
            data_size_bytes=actual_data_size,
            success=success,
            billable=effective_billable,
            tenant_id=_normalize_dimension(tenant_id, "tenant_id"),
            user_id=_normalize_dimension(user_id, "user_id"),
            session_id=_normalize_dimension(session_id, "session_id"),
        )

        with self._lock:
            self._records.append(record)

        log_method = logger.info if success else logger.warning
        log_method("Sorgu kullanımı kaydedildi", extra=record.as_log_extra())
        return record

    def get_records(
        self,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> tuple[UsageRecord, ...]:
        """Opsiyonel SaaS boyutlarına göre kayıtların değiştirilemez kopyasını döndürür."""
        with self._lock:
            records = tuple(self._records)

        return tuple(
            record
            for record in records
            if (tenant_id is None or record.tenant_id == tenant_id)
            and (user_id is None or record.user_id == user_id)
            and (session_id is None or record.session_id == session_id)
        )

    def summarize(
        self,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> UsageSummary:
        """Seçilen kullanıcı/tenant/oturum için kullanım toplamlarını döndürür."""
        records = self.get_records(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )

        return UsageSummary(
            total_events=len(records),
            total_query_count=sum(record.query_count for record in records),
            successful_query_count=sum(
                record.query_count for record in records if record.success
            ),
            failed_query_count=sum(
                record.query_count for record in records if not record.success
            ),
            billable_query_count=sum(
                record.query_count for record in records if record.billable
            ),
            total_row_count=sum(record.row_count for record in records),
            total_data_size_bytes=sum(record.data_size_bytes for record in records),
            billable_data_size_bytes=sum(
                record.data_size_bytes for record in records if record.billable
            ),
        )

    def reset(self) -> None:
        """Test/demo amacıyla process içi kayıtları temizler."""
        with self._lock:
            self._records.clear()


usage_tracker = UsageTracker()


def track_query_usage(**kwargs: Any) -> UsageRecord:
    """Global usage tracker üzerinde sorgu kullanımını kaydeden kısa yol."""
    return usage_tracker.record_query(**kwargs)
